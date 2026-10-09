import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bcrypt
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.entities import ActiveStatus, Role, User


async def init_admin(username: str, password: str) -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(User).where(User.username == username))
        if existing:
            raise SystemExit(f"user already exists: {username}")
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        session.add(User(username=username, password_hash=password_hash, role=Role.ADMIN, status=ActiveStatus.ACTIVE, must_change_password=False))
        await session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    asyncio.run(init_admin(args.username, args.password))
