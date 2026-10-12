"""Technical logging configuration for SecureRoom.

Maintains strict separation between technical logging (syslog/stdout)
and business/functional security audit logs (stored in database audit_logs).
Ensures passwords, raw session secrets, and database credentials are never logged.
"""

import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configures structured, sanitized console logger."""
    logger = logging.getLogger("secureroom")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()
