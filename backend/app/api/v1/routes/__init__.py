# This makes 'auth' and 'notification' importable from 'routes'
from .auth import router as auth_router
from .notification import router as notification_router

