"""
Feature Flag Dependencies
"""

from functools import wraps
from typing import Callable, Coroutine, TypeVar, ParamSpec

from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.feature_flags.models import FeatureFlag
from app.modules.feature_flags.service import FeatureFlagService

P = ParamSpec("P")
R = TypeVar("R")


def feature_required(feature_key: str) -> Callable[[Callable[P, Coroutine[None, None, R]]], Callable[P, Coroutine[None, None, R]]]:
    """
    Decorator to check if a feature is enabled for the current user
    """
    def decorator(func: Callable[P, Coroutine[None, None, R]]) -> Callable[P, Coroutine[None, None, R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request: Request = kwargs.get("request")
            if not request:
                raise ValueError("Request object not found in kwargs")

            user_id = request.state.user_id  # Assuming user_id is set in middleware
            db: AsyncSession = request.state.db

            service = FeatureFlagService(db)
            if not await service.is_feature_enabled(user_id, feature_key):
                raise HTTPException(
                    status_code=403,
                    detail=f"Feature '{feature_key}' is not enabled for your account",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
