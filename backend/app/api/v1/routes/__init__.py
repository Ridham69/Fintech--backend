# This makes all routers importable from 'routes'
from .auth import router as auth_router
from .notification import router as notification_router

__all__ = [
    "auth_router",
    "notification_router",
]

