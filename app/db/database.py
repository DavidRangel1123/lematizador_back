import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:  
  raise RuntimeError("DATABASE URL is not set")

engine = create_async_engine(
  DATABASE_URL,
  echo=False,
  future=True
)

AsyncSessionLocal = async_sessionmaker(
  bind=engine,
  class_=AsyncSession,
  expire_on_commit=False
)

class Base(DeclarativeBase):
  pass

async def get_db() -> AsyncSession:
  async with AsyncSessionLocal() as session:
    yield session