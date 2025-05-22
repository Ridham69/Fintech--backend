from sqlalchemy import Column, String
import uuid
from sqlalchemy.types import TypeDecorator, CHAR
from app.models.types import GUID as PG_UUID

class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise stores as stringified hex values.
    """
    impl = CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_GUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(value))
        else:
            return str(value) if dialect.name != 'postgresql' else value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(value)
