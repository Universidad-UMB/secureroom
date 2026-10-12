"""SecureRoom configuration loaded from environment variables and ``.env``."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    app_name: str = "SecureRoom"
    app_env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000

    # Database configuration
    database_url: str = Field(
        default="postgresql+psycopg2://secureroom_user:secureroom_password@localhost:5432/secureroom",
    )
    # Development defaults to the in-memory repositories. Set this to false
    # when PostgreSQL and the Alembic schema are available.
    use_in_memory_db: bool | None = None

    # Session & Security
    session_secret: str = Field(
        default="insecure_default_secret_key_change_me_in_production_32chars",
    )
    session_cookie_name: str = "secureroom_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"
    session_cookie_httponly: bool = True
    session_max_age_seconds: int = 28800  # 8 hours

    # Rate limiting for login
    login_max_failed_attempts: int = 5
    login_lockout_seconds: int = 300  # 5 minutes

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def effective_cookie_secure(self) -> bool:
        if self.is_production:
            return True
        return self.session_cookie_secure

    @property
    def effective_use_in_memory_db(self) -> bool:
        """Use in-memory repositories by default in development only."""
        if self.use_in_memory_db is not None:
            return self.use_in_memory_db
        return not self.is_production


# Singleton instance
settings = Settings()
