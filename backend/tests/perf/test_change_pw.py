"""Reproduce the change-password 500 bug."""
import asyncio
import traceback
from datetime import datetime, timezone

from app.database import async_session
from app.security import hash_password, verify_password
from sqlalchemy import select, update as sa_update
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.user_session import UserSession
from app.services.audit import log_audit


async def test():
    async with async_session() as db:
        # Load admin
        r = await db.execute(select(User).where(User.email == "admin@test.local"))
        user = r.scalar_one()
        print(f"User: {user.email}, id: {user.id}")

        # Simulate exact change-password flow
        now = datetime.now(timezone.utc)

        # Update password
        user.hashed_password = hash_password("NewTestPass123!")
        user.failed_login_attempts = 0
        user.locked_until = None

        # Revoke sessions
        await db.execute(sa_update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked_at=now))
        await db.execute(sa_update(UserSession).where(UserSession.user_id == user.id).values(revoked_at=now))

        # Audit log
        await log_audit(db, "password_change", user_id=user.id)

        await db.commit()
        print("Change 1 committed OK")

        # Second change - reload user
        r2 = await db.execute(select(User).where(User.email == "admin@test.local"))
        user2 = r2.scalar_one()
        print(f"Verify NewTestPass123! works: {verify_password('NewTestPass123!', user2.hashed_password)}")

        user2.hashed_password = hash_password("testpass123")
        user2.failed_login_attempts = 0
        user2.locked_until = None

        now2 = datetime.now(timezone.utc)
        await db.execute(sa_update(RefreshToken).where(RefreshToken.user_id == user2.id).values(revoked_at=now2))
        await db.execute(sa_update(UserSession).where(UserSession.user_id == user2.id).values(revoked_at=now2))

        await log_audit(db, "password_change", user_id=user2.id)

        await db.commit()
        print("Change 2 committed OK")


if __name__ == "__main__":
    asyncio.run(test())
