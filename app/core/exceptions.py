"""Domain and application exceptions for SecureRoom.

These exceptions represent specific business rule violations or security failures.
They are caught at the HTTP/Router layer to render controlled user messages
without disclosing stack traces, internal paths, or database details.
"""


class SecureRoomError(Exception):
    """Base exception for all SecureRoom domain errors."""

    def __init__(self, message: str = "An unexpected error occurred."):
        super().__init__(message)
        self.message = message


class AuthenticationError(SecureRoomError):
    """Raised when authentication fails (invalid credentials, expired session, inactive account)."""

    def __init__(self, message: str = "Credenciales inválidas o sesión no válida."):
        super().__init__(message)


class AuthorizationError(SecureRoomError):
    """Raised when a user attempts an action outside their role or resource ownership."""

    def __init__(self, message: str = "No tiene permisos para realizar esta acción."):
        super().__init__(message)


class ResourceNotFoundError(SecureRoomError):
    """Raised when a requested resource (room, user, reservation) does not exist."""

    def __init__(self, message: str = "El recurso solicitado no fue encontrado."):
        super().__init__(message)


class ValidationError(SecureRoomError):
    """Raised when business validation rules fail."""

    def __init__(self, message: str = "Los datos proporcionados no son válidos."):
        super().__init__(message)


class ReservationConflictError(SecureRoomError):
    """Raised when a reservation overlaps with an existing active reservation."""

    def __init__(
        self,
        message: str = "La sala no está disponible en el horario solicitado debido a un solapamiento.",
    ):
        super().__init__(message)


class CSRFError(SecureRoomError):
    """Raised when CSRF token is missing or invalid."""

    def __init__(self, message: str = "Token CSRF inválido o ausente. Intente nuevamente."):
        super().__init__(message)


class RateLimitError(SecureRoomError):
    """Raised when rate limiting thresholds are exceeded (e.g. repeated failed logins)."""

    def __init__(
        self,
        message: str = "Demasiados intentos fallidos. Intente nuevamente en unos minutos.",
        retry_after: int = 300,
    ):
        super().__init__(message)
        self.retry_after = retry_after
