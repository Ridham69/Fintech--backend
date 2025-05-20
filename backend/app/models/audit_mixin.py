from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func
from typing import Any

class AuditMixin:
    """
    Mixin for automatic created_at and updated_at timestamp fields.
    Use with SQLAlchemy declarative models for audit tracking.
    """
    created_at: Any = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Timestamp when the record was created"
    )
    updated_at: Any = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Timestamp when the record was last updated"
    )