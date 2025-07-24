# core/db.py
import json
import os
from typing import AsyncGenerator, Generator

from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from contextlib import asynccontextmanager, contextmanager
 
from core.settings import settings

# export environment variables
USER_FILE = settings.USER_FILE
DATABASE_URL = settings.DATABASE_URL

# === File-based user store (temporary IdP layer) ===
def load_users():
    if not os.path.exists(USER_FILE):
        return {"users": []}
    with open(USER_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=2)

# === Business SQLModel DB ===

# Sync Engine - Improved SQLite config for better concurrency
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Turn off debug logging in dev
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,  # Recycle connections every 5 minutes
    poolclass=StaticPool,  # Use static pool for SQLite
    connect_args={
        "check_same_thread": False,  # Allow multi-threading
        "timeout": 20,  # 20s timeout for database locks
        "isolation_level": None,  # Use autocommit mode
    },
)

# Async Engine - Convert sqlite:// to sqlite+aiosqlite://
async_database_url = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
async_engine = create_async_engine(
    async_database_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,
        "timeout": 20,
    },
)

def init_db():
    """Initialize database tables (sync)"""
    SQLModel.metadata.create_all(engine)

async def init_db_async():
    """Initialize database tables (async)"""
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

# Sync session management
def get_session() -> Generator[Session, None, None]:
    """Dependency for FastAPI sync endpoints"""
    with Session(engine) as session:
        yield session

@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Context manager for sync database operations"""
    with Session(engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# Async session management
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI async endpoints"""
    async with AsyncSession(async_engine) as session:
        yield session

@asynccontextmanager
async def get_async_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for async database operations"""
    async with AsyncSession(async_engine) as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()