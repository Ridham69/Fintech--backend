"""
Feature Flag Service
"""

from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_class import get_db
from app.modules.feature_flags.models import FeatureFlag


class FeatureFlagService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_feature_enabled(self, user_id: str, feature_key: str) -> bool:
        """
        Check if a feature is enabled for a user
        """
        feature = await self._get_feature_by_key(feature_key)
        if not feature:
            return False

        # Check if feature is globally disabled
        if not feature.enabled:
            return False

        # Check if feature has expired
        if feature.expires_at and feature.expires_at < datetime.utcnow():
            return False

        # If no rollout percentage, return enabled status
        if not feature.rollout_percentage:
            return True

        # Calculate user bucket based on user_id hash
        import hashlib
        hash_obj = hashlib.sha256()
        hash_obj.update(f"{feature_key}_{user_id}".encode())
        user_bucket = int(hash_obj.hexdigest(), 16) % 100

        return user_bucket < feature.rollout_percentage

    async def get_all_flags(self) -> List[FeatureFlag]:
        """
        Get all feature flags
        """
        result = await self.db.execute(
            "SELECT * FROM feature_flags ORDER BY created_at DESC"
        )
        return result.scalars().all()

    async def create_flag(
        self,
        key: str,
        enabled: bool = False,
        rollout_percentage: Optional[int] = None,
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        user_segment: Optional[str] = None,
    ) -> FeatureFlag:
        """
        Create a new feature flag
        """
        if rollout_percentage is not None and (rollout_percentage < 0 or rollout_percentage > 100):
            raise ValueError("Rollout percentage must be between 0 and 100")

        flag = FeatureFlag(
            key=key,
            enabled=enabled,
            rollout_percentage=rollout_percentage,
            description=description,
            expires_at=expires_at,
            user_segment=user_segment,
        )
        self.db.add(flag)
        await self.db.commit()
        await self.db.refresh(flag)
        return flag

    async def update_flag(
        self,
        key: str,
        enabled: Optional[bool] = None,
        rollout_percentage: Optional[int] = None,
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        user_segment: Optional[str] = None,
    ) -> FeatureFlag:
        """
        Update an existing feature flag
        """
        flag = await self._get_feature_by_key(key)
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")

        if enabled is not None:
            flag.enabled = enabled
        if rollout_percentage is not None:
            if rollout_percentage < 0 or rollout_percentage > 100:
                raise ValueError("Rollout percentage must be between 0 and 100")
            flag.rollout_percentage = rollout_percentage
        if description is not None:
            flag.description = description
        if expires_at is not None:
            flag.expires_at = expires_at
        if user_segment is not None:
            flag.user_segment = user_segment

        await self.db.commit()
        await self.db.refresh(flag)
        return flag

    async def _get_feature_by_key(self, key: str) -> Optional[FeatureFlag]:
        """
        Get feature flag by key
        """
        result = await self.db.execute(
            "SELECT * FROM feature_flags WHERE key = :key",
            {"key": key},
        )
        return result.scalar()
