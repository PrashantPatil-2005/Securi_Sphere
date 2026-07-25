import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine("postgresql+asyncpg://securi:securi_dev@127.0.0.1:5432/securi")
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT u.email, r.name as role, u.is_active, u.hashed_password IS NOT NULL as has_password FROM users u LEFT JOIN roles r ON u.role_id = r.id WHERE u.email = 'admin@test.local'"))
        row = r.fetchone()
        if row:
            print("admin@test.local:", dict(row._mapping))
        else:
            print("admin@test.local not found")

        r2 = await conn.execute(text("SELECT u.email, r.name as role FROM users u LEFT JOIN roles r ON u.role_id = r.id"))
        for row2 in r2:
            print(dict(row2._mapping))
    await engine.dispose()

asyncio.run(main())
