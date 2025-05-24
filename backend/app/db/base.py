"""
SQLAlchemy Base Module

This module provides the declarative base for SQLAlchemy models with:
- Naming conventions for consistent migrations
- Common model mixins
- Type annotation support
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Naming convention for constraints and indices
# This helps Alembic generate consistent migrations
convention: Dict[str, Any] = {
    "ix": "ix_%(column_0_label)s",  # Index
    "uq": "uq_%(table_name)s_%(column_0_name)s",  # Unique constraint
    "ck": "ck_%(table_name)s_%(constraint_name)s",  # Check constraint
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # Foreign key
    "pk": "pk_%(table_name)s"  # Primary key
}

# Create metadata with naming convention
metadata = MetaData(naming_convention=convention)

class Base(DeclarativeBase):
    """Base class for all database models."""
    
    metadata = metadata
    
    # Auto-generate table name from class name
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    # Common columns for all tables
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

# Create empty models package
from . import models  # noqa 
