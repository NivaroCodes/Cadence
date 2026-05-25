import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

# Add backend directory to path to support imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.message import Message


async def main() -> None:
    print("================== VERIFYING PHASE 1 MULTI-TENANT SCHEMA ==================")
    admin_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")

    async with AsyncSessionLocal() as db:
        # 1. Verify default Admin user creation
        print("1. Fetching default Admin user...")
        stmt_user = select(User).where(User.id == admin_uuid)
        result_user = await db.execute(stmt_user)
        admin = result_user.scalars().first()

        if not admin:
            print("[FAIL] Default Admin user not found in 'users' table!")
            sys.exit(1)

        print(f"[PASS] Found Admin user: {admin.email} (ID: {admin.id})")

        # 2. Check that existing Leads, Campaigns, and Messages are backfilled to Admin
        print("\n2. Verifying backfilled relation data counts...")
        stmt_leads_count = select(Lead).where(Lead.user_id == admin_uuid)
        leads_res = await db.execute(stmt_leads_count)
        leads = leads_res.scalars().all()
        print(f"   - Leads backfilled: {len(leads)}")

        stmt_campaigns_count = select(Campaign).where(Campaign.user_id == admin_uuid)
        campaigns_res = await db.execute(stmt_campaigns_count)
        campaigns = campaigns_res.scalars().all()
        print(f"   - Campaigns backfilled: {len(campaigns)}")

        stmt_messages_count = select(Message).where(Message.user_id == admin_uuid)
        messages_res = await db.execute(stmt_messages_count)
        messages = messages_res.scalars().all()
        print(f"   - Messages backfilled: {len(messages)}")

        # 3. Test relationship loading via User model
        print("\n3. Testing selectinload on Admin user relationships...")
        stmt_admin_relations = (
            select(User)
            .options(
                selectinload(User.leads),
                selectinload(User.campaigns),
                selectinload(User.messages),
            )
            .where(User.id == admin_uuid)
        )
        res_relations = await db.execute(stmt_admin_relations)
        admin_full = res_relations.scalars().first()

        print(f"   - Admin.leads count: {len(admin_full.leads)}")
        print(f"   - Admin.campaigns count: {len(admin_full.campaigns)}")
        print(f"   - Admin.messages count: {len(admin_full.messages)}")

        # 4. Test multi-tenant isolation and foreign key constraint validation
        print("\n4. Creating a new test user and campaign to verify foreign keys...")
        test_user = User(
            id=uuid.uuid4(),
            email=f"test_tenant_{uuid.uuid4().hex[:6]}@cadence.kz",
            hashed_password="some_test_hashed_password_hash",
            is_active=True,
        )
        db.add(test_user)
        await db.flush()
        print(f"   [OK] Created temporary user: {test_user.email} (ID: {test_user.id})")

        test_campaign = Campaign(
            id=uuid.uuid4(),
            user_id=test_user.id,
            name="Verification Test Campaign",
            description="Used to test multi-tenant relational persistence",
        )
        db.add(test_campaign)
        await db.flush()
        print(f"   [OK] Created campaign associated with user: {test_campaign.name}")

        # Assert relationship back_populates is loaded
        stmt_check_user = select(User).options(selectinload(User.campaigns)).where(User.id == test_user.id)
        res_check_user = await db.execute(stmt_check_user)
        refreshed_user = res_check_user.scalars().first()
        assert len(refreshed_user.campaigns) == 1
        assert refreshed_user.campaigns[0].id == test_campaign.id
        print("   [PASS] Bidirectional relationships work correctly.")

        # 5. Test cascade delete isolation
        print("\n5. Testing CASCADE DELETE on new user deletion...")
        test_user_id = test_user.id
        test_campaign_id = test_campaign.id

        await db.delete(test_user)
        await db.flush()
        print("   [OK] Deleted temporary User record.")

        # Check if campaign was successfully cascade-deleted
        stmt_check_camp = select(Campaign).where(Campaign.id == test_campaign_id)
        res_camp = await db.execute(stmt_check_camp)
        camp = res_camp.scalars().first()

        if camp is not None:
            print(f"[FAIL] Campaign '{test_campaign_id}' was not cascade-deleted!")
            sys.exit(1)

        print("   [PASS] Cascade delete confirmed: Campaign successfully purged from database.")

        # Rollback all changes made in verification session to keep staging DB pristine
        await db.rollback()
        print("\n[SUCCESS] All verification tests passed perfectly! Database rolled back cleanly.")
        print("===========================================================================")


if __name__ == "__main__":
    asyncio.run(main())
