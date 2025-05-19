"""
Feature Flag Router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_admin
from app.db.base_class import get_db
from app.modules.feature_flags.models import FeatureFlag
from app.modules.feature_flags.service import FeatureFlagService

router = APIRouter(prefix="/feature-flags", tags=["Feature Flags"])


@router.get("/")
async def list_feature_flags(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin),
) -> list[FeatureFlag]:
    """
    List all feature flags (admin only)
    """
    service = FeatureFlagService(db)
    return await service.get_all_flags()


@router.post("/")
async def create_feature_flag(
    key: str,
    enabled: bool = False,
    rollout_percentage: Optional[int] = None,
    description: Optional[str] = None,
    expires_at: Optional[str] = None,
    user_segment: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin),
) -> FeatureFlag:
    """
    Create a new feature flag (admin only)
    """
    service = FeatureFlagService(db)
    return await service.create_flag(
        key=key,
        enabled=enabled,
        rollout_percentage=rollout_percentage,
        description=description,
        expires_at=expires_at,
        user_segment=user_segment,
    )


@router.patch("/{feature_key}")
async def update_feature_flag(
    feature_key: str,
    enabled: Optional[bool] = None,
    rollout_percentage: Optional[int] = None,
    description: Optional[str] = None,
    expires_at: Optional[str] = None,
    user_segment: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin),
) -> FeatureFlag:
    """
    Update an existing feature flag (admin only)
    """
    service = FeatureFlagService(db)
    return await service.update_flag(
        key=feature_key,
        enabled=enabled,
        rollout_percentage=rollout_percentage,
        description=description,
        expires_at=expires_at,
        user_segment=user_segment,
    )
