from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import settings


# TODO: create the async engine using settings.database_url
# Hint: create_async_engine(url, echo=True) — echo=True logs all SQL, useful while learning
engine = None  # replace this

# TODO: create an async session factory
# Hint: sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
AsyncSessionLocal = None  # replace this


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency — yields a database session."""
    # TODO: implement this as an async context manager that yields a session
    # Pattern:
    #   async with AsyncSessionLocal() as session:
    #       yield session
    raise NotImplementedError
