"""
Feature Flag Models
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

from app.db.base_class import Base


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    enabled = Column(Boolean, default=False)
    rollout_percentage = Column(Integer, nullable=True)  # 0-100
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    user_segment = Column(String(50), nullable=True)  # For future extension

    def __repr__(self) -> str:
        return f"<FeatureFlag {self.key} ({'enabled' if self.enabled else 'disabled'})>"
