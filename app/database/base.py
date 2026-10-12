"""SQLAlchemy Declarative Base and schema definitions for SecureRoom.

Supports native SQLAlchemy 2.0+ in production/Docker, with transparent
fallback shims if run in environments without the SQLAlchemy package installed.
"""

try:
    import sqlalchemy
    from sqlalchemy.orm import declarative_base, relationship
    from sqlalchemy import (
        Column,
        String,
        Integer,
        Boolean,
        DateTime,
        Text,
        ForeignKey,
        CheckConstraint,
        Index,
    )
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID

    Base = declarative_base()
    HAS_SQLALCHEMY = True

except ImportError:
    HAS_SQLALCHEMY = False

    class _BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def declarative_base():
        return _BaseModel

    class Column:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class String:
        def __init__(self, *args, **kwargs): pass

    class Integer:
        def __init__(self, *args, **kwargs): pass

    class Boolean:
        def __init__(self, *args, **kwargs): pass

    class DateTime:
        def __init__(self, *args, **kwargs): pass

    class Text:
        def __init__(self, *args, **kwargs): pass

    class ForeignKey:
        def __init__(self, *args, **kwargs): pass

    class CheckConstraint:
        def __init__(self, *args, **kwargs): pass

    class Index:
        def __init__(self, *args, **kwargs): pass

    class PG_UUID:
        def __init__(self, *args, **kwargs): pass

    def relationship(*args, **kwargs):
        return None

    Base = declarative_base()
