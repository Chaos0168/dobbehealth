from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
# "async" engine — never blocks the event loop while waiting for DB
engine = create_async_engine(
    settings.database_url,
    echo=False,          # set True to print all SQL in terminal (useful for debugging)
    pool_size=10,        # max 10 simultaneous DB connections
    max_overflow=20,
)

# ── Session factory ───────────────────────────────────────────────────────────
# Every request gets its own session (like a "conversation" with the DB)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,   # keep objects usable after commit
)

# ── Base class for all models ─────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass

# ── Dependency injected into every FastAPI route that needs DB ────────────────
async def get_db():
    """
    FastAPI dependency. Usage in routes:
        async def my_route(db: AsyncSession = Depends(get_db)):
    Automatically opens and closes session per request.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
