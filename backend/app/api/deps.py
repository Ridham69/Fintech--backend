# FastAPI dependencies
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session  # Make sure this is your async sessionmaker

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async SQLAlchemy session.
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

def get_current_user():
    """
    Placeholder for user authentication dependency.
    Replace with real authentication logic (e.g., JWT, OAuth2).
    """
    return {"username": "mockuser"}
