"""
SQLite connection using aiosqlite.

For prototype: SQLite file at /app/data/governance.db (ephemeral in Cloud Run).
For production: swap DATABASE_URL to postgresql+asyncpg://... and replace this
module with the asyncpg version — no changes needed in routers.

Row factory returns dict-like objects so router code is DB-agnostic.
"""

import os
import logging
import aiosqlite

logger = logging.getLogger(__name__)

# SQLite file path — use /tmp for Cloud Run (ephemeral but writable)
_DB_PATH = os.getenv("DATABASE_URL", "sqlite:////tmp/governance.db").replace("sqlite+aiosqlite://", "").replace("sqlite://", "")

_db: aiosqlite.Connection | None = None


async def init_pool() -> None:
    """Open SQLite connection and run schema + seed."""
    global _db
    import os as _os
    db_dir = _os.path.dirname(_DB_PATH)
    if db_dir:
        _os.makedirs(db_dir, exist_ok=True)

    _db = await aiosqlite.connect(_DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA foreign_keys=ON")
    logger.info("SQLite connected: %s", _DB_PATH)
    await _run_migrations()


async def close_pool() -> None:
    global _db
    if _db:
        await _db.close()
        _db = None
        logger.info("SQLite connection closed")


def get_pool():
    """Return the active DB connection (acts as the pool for SQLite)."""
    if _db is None:
        raise RuntimeError("DB not initialised — call init_pool() on startup")
    return _db


async def fetchrow(query: str, *args):
    """Fetch a single row. Returns dict or None."""
    db = get_pool()
    async with db.execute(query, args) as cursor:
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)


async def fetch(query: str, *args) -> list[dict]:
    """Fetch all rows."""
    db = get_pool()
    async with db.execute(query, args) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def execute(query: str, *args) -> str:
    """Execute a write query. Returns rowcount string like asyncpg."""
    db = get_pool()
    async with db.execute(query, args) as cursor:
        await db.commit()
        return f"EXECUTE {cursor.rowcount}"


async def executemany(query: str, args_list: list) -> None:
    """Execute a query for multiple argument sets."""
    db = get_pool()
    await db.executemany(query, args_list)
    await db.commit()


async def _run_migrations() -> None:
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    seed_path   = os.path.join(os.path.dirname(__file__), "seed.sql")

    with open(schema_path) as f:
        schema_sql = f.read()
    await _db.executescript(schema_sql)
    logger.info("Schema applied")

    with open(seed_path) as f:
        seed_sql = f.read()
    await _db.executescript(seed_sql)
    logger.info("Seed data applied")
    await _db.commit()
