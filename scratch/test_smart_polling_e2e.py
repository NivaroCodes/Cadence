"""
E2E test for Smart Polling reply detection.

Usage (from repo root):
  cd backend
  python ..\scratch\test_smart_polling_e2e.py

Requires .env with DATABASE_URL and at least one seq-1 sent Message in DB.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.message import Message, MessageStatus
from app.services.campaign_runner import CampaignRunner


def _make_session() -> async_sessionmaker:
    url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
        "postgres://", "postgresql+asyncpg://", 1
    )
    engine = create_async_engine(
        url,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
    )
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def main() -> None:
    SessionLocal = _make_session()

    async with SessionLocal() as db:
        stmt = (
            select(Message)
            .options(selectinload(Message.lead))
            .where(Message.sequence_number == 1)
            .where(Message.status == MessageStatus.sent)
            .order_by(Message.sent_at.desc())
        )
        result = await db.execute(stmt)
        message = result.scalars().first()

    if not message:
        print("No seq-1 sent message found. Run a campaign first.")
        return

    print(f"Testing message: {message.id}")
    print(f"  Lead email:      {message.lead.email}")
    print(f"  Sent at:         {message.sent_at}")
    print(f"  Status (before): {message.status}")
    print(f"  Attempts (before): {message.reply_check_attempts}")

    attempts_before = message.reply_check_attempts

    runner = CampaignRunner()
    await runner.check_replies_for_message(message.id)

    async with SessionLocal() as db:
        result = await db.execute(select(Message).where(Message.id == message.id))
        updated = result.scalars().first()

    print(f"\n  Status (after):  {updated.status}")
    print(f"  Attempts (after): {updated.reply_check_attempts}")

    if updated.status == MessageStatus.replied:
        print("\nPASS -- Reply detected, status updated to replied")
    elif updated.reply_check_attempts == attempts_before + 1:
        print("\nPASS -- No reply found, attempt counter incremented correctly")
    else:
        print("\nFAIL -- reply_check_attempts did not increment and status unchanged")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
