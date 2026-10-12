"""SecureRoom Configuration Module.

Handles environment variables and application settings using Pydantic.
Ensures security defaults (HttpOnly, Lax cookies, external secrets).
"""

import os
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    app_name: str = "SecureRoom"
    app_env: str = Field(default="development", env="APP_ENV")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")

    # Database configuration
    database_url: str = Field(
        default="postgresql://secureroom_user:secureroom_password@localhost:5432/secureroom",
        env="DATABASE_URL",
    )

    # Session & Security
    session_secret: str = Field(
        default="insecure_default_secret_key_change_me_in_production_32chars",
        env="SESSION_SECRET",
    )
    session_cookie_name: str = "secureroom_session"
    session_cookie_secure: bool = Field(default=False, env="SESSION_COOKIE_SECURE")
    session_cookie_samesite: str = "lax"
    session_cookie_httponly: bool = True
    session_max_age_seconds: int = Field(default=28800, env="SESSION_MAX_AGE_SECONDS")  # 8 hours

    # Rate limiting for login
    login_max_failed_attempts: int = 5
    login_lockout_seconds: int = 300  # 5 minutes

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def effective_cookie_secure(self) -> bool:
        if self.is_production:
            return True
        return self.session_cookie_secure


# Singleton instance
settings = Settings()
