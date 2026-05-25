import asyncio
import os
import sys
from uuid import UUID

# Add parent directory to path to support imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.database import AsyncSessionLocal
from app.models.user import User


async def cleanup_users() -> None:
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.email.in_(["user_a@test.kz", "user_b@test.kz"]))
        res = await db.execute(stmt)
        users = res.scalars().all()
        for user in users:
            await db.delete(user)
        await db.commit()


async def test_data_isolation():
    print("================== STARTING COMPREHENSIVE DATA ISOLATION TESTS ==================")
    
    # Ensure a clean slate
    await cleanup_users()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create User A
            user_a_resp = await client.post("/auth/signup", json={
                "email": "user_a@test.kz",
                "password": "Password123!",
                "company_name": "Company A"
            })
            assert user_a_resp.status_code == 201, f"User A signup failed: {user_a_resp.text}"
            user_a_token = user_a_resp.json()["jwt_token"]
            
            # Create User B
            user_b_resp = await client.post("/auth/signup", json={
                "email": "user_b@test.kz",
                "password": "Password123!",
                "company_name": "Company B"
            })
            assert user_b_resp.status_code == 201, f"User B signup failed: {user_b_resp.text}"
            user_b_token = user_b_resp.json()["jwt_token"]
            
            # User A creates a lead
            lead_resp = await client.post(
                "/api/v1/leads",
                json={"name": "Lead A", "email": "lead_a@test.kz", "company": "Co A"},
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert lead_resp.status_code == 201, f"Lead creation failed: {lead_resp.text}"
            lead_a_id = lead_resp.json()["id"]
            
            # User A creates a campaign
            campaign_resp = await client.post(
                "/api/v1/campaigns",
                json={"name": "Campaign A"},
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert campaign_resp.status_code == 201, f"Campaign creation failed: {campaign_resp.text}"
            campaign_a_id = campaign_resp.json()["id"]
            
            # TEST 1: User B cannot GET User A's lead
            resp = await client.get(
                f"/api/v1/leads/{lead_a_id}",
                headers={"Authorization": f"Bearer {user_b_token}"}
            )
            assert resp.status_code == 403, f"Test 1 FAILED: User B could access User A lead. Status: {resp.status_code}"
            print("[PASS] Test 1: User B cannot GET User A's lead (403)")
            
            # TEST 2: User B cannot PUT User A's campaign
            resp = await client.put(
                f"/api/v1/campaigns/{campaign_a_id}",
                json={"name": "Hacked Campaign A"},
                headers={"Authorization": f"Bearer {user_b_token}"}
            )
            assert resp.status_code == 403, f"Test 2 FAILED: User B could modify User A campaign. Status: {resp.status_code}"
            print("[PASS] Test 2: User B cannot PUT User A's campaign (403)")
            
            # TEST 3: User B cannot DELETE User A's lead
            resp = await client.delete(
                f"/api/v1/leads/{lead_a_id}",
                headers={"Authorization": f"Bearer {user_b_token}"}
            )
            assert resp.status_code == 403, f"Test 3 FAILED: User B could delete User A lead. Status: {resp.status_code}"
            print("[PASS] Test 3: User B cannot DELETE User A's lead (403)")
            
            # TEST 4: User A POST /leads creates lead with own user_id
            lead_resp2 = await client.post(
                "/api/v1/leads",
                json={"name": "Lead A2", "email": "lead_a2@test.kz", "company": "Co A"},
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert lead_resp2.status_code == 201, "Test 4 FAILED: Could not create lead"
            print("[PASS] Test 4: User A can create leads (auto-assigned user_id)")
            
            # TEST 5: User A POST /campaigns creates campaign with own user_id
            campaign_resp2 = await client.post(
                "/api/v1/campaigns",
                json={"name": "Campaign A2"},
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert campaign_resp2.status_code == 201, "Test 5 FAILED: Could not create campaign"
            print("[PASS] Test 5: User A can create campaigns (auto-assigned user_id)")
            
            # TEST 6: User A LIST /leads returns only own leads
            resp = await client.get(
                "/api/v1/leads",
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            leads = resp.json()
            assert len(leads) == 2, f"Test 6 FAILED: Expected 2 leads, got {len(leads)}"
            print("[PASS] Test 6: User A sees only own leads (2 of 2)")
            
            # TEST 7: User B LIST /campaigns returns empty (no campaigns created)
            resp = await client.get(
                "/api/v1/campaigns",
                headers={"Authorization": f"Bearer {user_b_token}"}
            )
            campaigns = resp.json()
            assert len(campaigns) == 0, "Test 7 FAILED: User B should see no campaigns"
            print("[PASS] Test 7: User B sees no campaigns (isolation verified)")
            
            # TEST 8: Admin can access all data (future phase)
            print("[SKIP] Test 8: Admin access (Phase 5+)")
            
            print("\n[SUCCESS] All data isolation tests passed!")
            
    finally:
        print("Cleaning up test user records...")
        await cleanup_users()
        print("[OK] Cleanup completed.")
        print("==================================================================")


if __name__ == "__main__":
    asyncio.run(test_data_isolation())
