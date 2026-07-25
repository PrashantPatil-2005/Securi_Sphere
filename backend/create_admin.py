import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine("postgresql+asyncpg://securi:securi_dev@127.0.0.1:5432/securi")
    async with engine.begin() as conn:
        await conn.execute(text("""
            INSERT INTO users (id, email, full_name, hashed_password, role_id, is_active, mfa_enabled, mfa_backup_codes, failed_login_attempts)
            SELECT 
                gen_random_uuid(),
                'admin@securi.local',
                'Admin User',
                '$2b$12$LJ3m4ys3Lk0TSwHjnF7bEOjCvMfhf6eHbXhjHjKj1k2l3m4n5o6p7',
                r.id,
                true,
                false,
                '[]',
                0
            FROM roles r WHERE r.name = 'admin'
            ON CONFLICT (email) DO NOTHING
        """))
        result = await conn.execute(text("SELECT email FROM users WHERE email = 'admin@securi.local'"))
        row = result.fetchone()
        if row:
            print(f"User admin@securi.local exists")
        else:
            print("Failed to create user")
    await engine.dispose()

asyncio.run(main())
