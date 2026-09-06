"""Purge all stale data using TRUNCATE CASCADE."""
import asyncio
from app.database import async_session
from sqlalchemy import text


TABLES = [
    "offense_events",
    "offenses",
    "attack_timelines",
    "alerts",
    "events",
    "enrollment_tokens",
    "in_app_notifications",
    "audit_logs",
    "metrics",
    "hosts",
]


async def purge():
    async with async_session() as db:
        for table in TABLES:
            try:
                await db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                print(f"{table}: truncated")
            except Exception as e:
                print(f"{table}: FAILED ({e.__class__.__name__})")
        await db.commit()
        print("Done")


if __name__ == "__main__":
    asyncio.run(purge())
