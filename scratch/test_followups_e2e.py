import asyncio
import json
import sys
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

# Adjust sys.path to backend directory to import database and models directly
import os
sys.path.insert(0, "C:\\dev\\Cadence\\backend")

from app.database import AsyncSessionLocal
from app.models.message import Message, MessageStatus, MessageChannel
from app.services.campaign_runner import CampaignRunner
from sqlalchemy import select

BASE_URL = "http://127.0.0.1:8000"


def make_request(method: str, path: str, payload: dict = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method
    )
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            body_text = response.read().decode("utf-8")
            body = json.loads(body_text) if body_text else None
            return status_code, body
    except urllib.error.HTTPError as e:
        status_code = e.code
        body_text = e.read().decode("utf-8")
        body = json.loads(body_text) if body_text else None
        return status_code, body
    except Exception as e:
        return 0, {"error": str(e)}


async def verify_followup_in_db(campaign_id: str) -> Message | None:
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Message)
            .where(Message.campaign_id == uuid.UUID(campaign_id))
            .where(Message.sequence_number == 2)
        )
        result = await session.execute(stmt)
        return result.scalars().first()


async def main():
    print("Starting E2E Follow-up sequencing validation...")
    
    # 1. Create a unique Lead (or use existing if already exists)
    unique_id = str(uuid.uuid4())[:8]
    lead_email = "nivaro.codes@gmail.com"
    lead_payload = {
        "name": f"Test Lead {unique_id}",
        "company": f"Test Company {unique_id}",
        "email": lead_email,
        "phone": "+77019998877",
        "linkedin_url": "https://linkedin.com/in/test",
        "website": "https://test.com",
        "industry": "Technology"
    }
    
    status, lead_data = make_request("POST", "/api/v1/leads", lead_payload)
    if status != 201:
        if isinstance(lead_data, dict) and "already exists" in str(lead_data.get("detail", "")):
            status_list, leads_list = make_request("GET", "/api/v1/leads")
            if status_list == 200:
                matching = [l for l in leads_list if l.get("email") == lead_email]
                if matching:
                    lead_data = matching[0]
                    print(f"[INFO] Using existing Lead {lead_data['id']}")
                else:
                    print(f"[FAIL] Lead exists but not found in list: {lead_data}")
                    sys.exit(1)
            else:
                print(f"[FAIL] Failed to list leads: {leads_list}")
                sys.exit(1)
        else:
            print(f"[FAIL] Failed to create lead: {lead_data}")
            sys.exit(1)
        
    lead_id = lead_data["id"]
    print(f"[PASS] Created Lead {lead_id} successfully")
    
    # 2. Create a Campaign
    campaign_payload = {
        "name": f"Follow-up Campaign {unique_id}",
        "description": "Campaign for testing follow-ups sequencing with backdated data",
        "tone": "casual",
        "language": "en",
        "lead_ids": [lead_id]
    }
    
    status, campaign_data = make_request("POST", "/api/v1/campaigns", campaign_payload)
    if status != 201:
        print(f"[FAIL] Failed to create campaign: {campaign_data}")
        sys.exit(1)
        
    campaign_id = campaign_data["id"]
    print(f"[PASS] Created Campaign {campaign_id} successfully")
    
    # 3. Seed backdated Message directly in DB (sequence 1, sent_at = 4 days ago)
    print("Seeding backdated sequence 1 message in database...")
    async with AsyncSessionLocal() as session:
        backdated_msg = Message(
            campaign_id=uuid.UUID(campaign_id),
            lead_id=uuid.UUID(lead_id),
            channel=MessageChannel.email,
            content="Initial outreach email content sent some days ago.",
            status=MessageStatus.sent,
            sequence_number=1,
            recipient_address=lead_email,
            sent_at=datetime.now(timezone.utc) - timedelta(days=4)
        )
        session.add(backdated_msg)
        await session.commit()
    print("[PASS] Successfully seeded backdated Message (sequence_number=1, sent_at=T-4 days)")
    
    # 4. Trigger run_followups() directly
    print("Triggering CampaignRunner().run_followups()...")
    runner = CampaignRunner()
    await runner.run_followups()
    print("[PASS] run_followups() completed")
    
    # 5. Check the database for the sent follow-up Message (sequence 2)
    print("Checking database for sequence 2 message...")
    msg_seq2 = await verify_followup_in_db(campaign_id)
    if not msg_seq2:
        print("[FAIL] Sequence 2 message not found in DB!")
        sys.exit(1)
        
    print("\n================== VALIDATION SUCCESS ==================")
    print(f"Message ID: {msg_seq2.id}")
    print(f"Campaign ID: {msg_seq2.campaign_id}")
    print(f"Lead ID: {msg_seq2.lead_id}")
    print(f"Channel: {msg_seq2.channel}")
    print(f"Recipient: {msg_seq2.recipient_address}")
    print(f"Sequence Number: {msg_seq2.sequence_number}")
    print(f"Status: {msg_seq2.status}")
    print(f"Sent At: {msg_seq2.sent_at}")
    print("------------------ Message Content ------------------")
    print(msg_seq2.content)
    print("========================================================\n")
    print("[PASS] E2E Follow-up sequence 2 Validation completed successfully!")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
