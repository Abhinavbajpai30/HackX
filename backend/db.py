import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base

DATABASE_URL = os.getenv("DATABASE_URL") or (
    "postgresql+asyncpg://neondb_owner:npg_Eid2TcmQLnG0"
    "@ep-sparkling-sunset-a1iowetz-pooler.ap-southeast-1.aws.neon.tech/neondb"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,              # Turn off SQL echo in production
    pool_pre_ping=True,      # Checks connections before using them
    pool_recycle=1800,       # Reconnect every 30 minutes
    pool_timeout=60,         # Wait 60s for a connection before raising
)

async_session_maker = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_async_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
