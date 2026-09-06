"""Check DB state and reproduce the 500."""
import asyncio
import json
from datetime import datetime, timezone

from app.database import async_session
from sqlalchemy import text


async def check():
    async with async_session() as db:
        # Check ingest_dedup table
        try:
            r = await db.execute(text("SELECT count(*) FROM ingest_dedup"))
            print(f"ingest_dedup table: {r.scalar_one()} rows")
        except Exception as e:
            print(f"ingest_dedup table ERROR: {e.__class__.__name__}: {e}")

        # Check tables
        r = await db.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ))
        tables = sorted([row[0] for row in r.fetchall()])
        print(f"Tables ({len(tables)}): {tables}")


if __name__ == "__main__":
    asyncio.run(check())
