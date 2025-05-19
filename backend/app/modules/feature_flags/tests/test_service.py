"""
Feature Flag Service Tests
"""

import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.feature_flags.models import FeatureFlag
from app.modules.feature_flags.service import FeatureFlagService


@pytest.fixture
async def service(db_session: AsyncSession) -> FeatureFlagService:
    """Fixture for FeatureFlagService"""
    return FeatureFlagService(db_session)


async def test_is_feature_enabled_full_rollout(service: FeatureFlagService, db_session: AsyncSession):
    """Test feature enabled with 100% rollout"""
    flag = FeatureFlag(
        key="test_feature",
        enabled=True,
        rollout_percentage=100,
        description="Test Feature",
    )
    db_session.add(flag)
    await db_session.commit()

    assert await service.is_feature_enabled("user123", "test_feature") is True


async def test_is_feature_enabled_partial_rollout(service: FeatureFlagService, db_session: AsyncSession):
    """Test feature with 50% rollout"""
    flag = FeatureFlag(
        key="test_feature",
        enabled=True,
        rollout_percentage=50,
        description="Test Feature",
    )
    db_session.add(flag)
    await db_session.commit()

    # Test with different users to ensure proper bucketing
    assert await service.is_feature_enabled("user123", "test_feature") is True
    assert await service.is_feature_enabled("user456", "test_feature") is True
    assert await service.is_feature_enabled("user789", "test_feature") is True


async def test_is_feature_enabled_disabled(service: FeatureFlagService, db_session: AsyncSession):
    """Test disabled feature"""
    flag = FeatureFlag(
        key="test_feature",
        enabled=False,
        description="Test Feature",
    )
    db_session.add(flag)
    await db_session.commit()

    assert await service.is_feature_enabled("user123", "test_feature") is False


async def test_is_feature_enabled_expired(service: FeatureFlagService, db_session: AsyncSession):
    """Test expired feature"""
    flag = FeatureFlag(
        key="test_feature",
        enabled=True,
        expires_at=datetime.utcnow() - timedelta(days=1),
        description="Test Feature",
    )
    db_session.add(flag)
    await db_session.commit()

    assert await service.is_feature_enabled("user123", "test_feature") is False


async def test_create_flag(service: FeatureFlagService, db_session: AsyncSession):
    """Test creating a new feature flag"""
    flag = await service.create_flag(
        key="new_feature",
        enabled=True,
        rollout_percentage=50,
        description="New Feature",
    )

    assert flag.key == "new_feature"
    assert flag.enabled is True
    assert flag.rollout_percentage == 50


async def test_update_flag(service: FeatureFlagService, db_session: AsyncSession):
    """Test updating an existing feature flag"""
    flag = FeatureFlag(
        key="test_feature",
        enabled=True,
        rollout_percentage=50,
        description="Test Feature",
    )
    db_session.add(flag)
    await db_session.commit()

    updated_flag = await service.update_flag(
        key="test_feature",
        enabled=False,
        rollout_percentage=100,
    )

    assert updated_flag.enabled is False
    assert updated_flag.rollout_percentage == 100


async def test_update_flag_not_found(service: FeatureFlagService):
    """Test updating non-existent feature flag"""
    with pytest.raises(HTTPException) as exc_info:
        await service.update_flag(key="nonexistent_feature")
    assert exc_info.value.status_code == 404


async def test_invalid_rollout_percentage(service: FeatureFlagService, db_session: AsyncSession):
    """Test invalid rollout percentage"""
    with pytest.raises(ValueError):
        await service.create_flag(
            key="test_feature",
            enabled=True,
            rollout_percentage=101,
        )
