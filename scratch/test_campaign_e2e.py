import asyncio
import json
import sys
import urllib.request
import uuid
from datetime import datetime

# Adjust sys.path to backend directory to import database and models directly
import os
sys.path.insert(0, "C:\\dev\\Cadence\\backend")

from app.database import AsyncSessionLocal
from app.models.message import Message, MessageStatus
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


async def verify_message_in_db(campaign_id: str) -> Message | None:
    async with AsyncSessionLocal() as session:
        stmt = select(Message).where(Message.campaign_id == uuid.UUID(campaign_id))
        result = await session.execute(stmt)
        return result.scalars().first()


async def main():
    print("Starting E2E Campaign Runner Validation...")
    
    # 1. Create a unique Lead
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
        print(f"[FAIL] Failed to create lead: {lead_data}")
        sys.exit(1)
        
    lead_id = lead_data["id"]
    print(f"[PASS] Created Lead {lead_id} successfully")
    
    # 2. Create a Campaign
    campaign_payload = {
        "name": f"Validation Campaign {unique_id}",
        "description": "Validation campaign testing background worker",
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
    
    # 3. Start the Campaign (triggers BackgroundTasks)
    print("Starting campaign via endpoint...")
    status, start_data = make_request("POST", f"/api/v1/campaigns/{campaign_id}/start")
    if status != 200:
        print(f"[FAIL] Failed to start campaign: {start_data}")
        sys.exit(1)
        
    print("[PASS] Start campaign endpoint returned 200 immediately")
    
    # 4. Wait and check the database for the sent Message
    print("Waiting for BackgroundTask CampaignRunner to run Gemini and send outreach...")
    
    message_found = None
    # Maximum 75 seconds timeout to accommodate 30s email sleep + Gemini execution
    for attempt in range(15):
        await asyncio.sleep(5)
        print(f"Checking DB for message (attempt {attempt + 1}/15)...")
        msg = await verify_message_in_db(campaign_id)
        if msg:
            message_found = msg
            break
            
    if not message_found:
        print("[FAIL] No message found in DB after 45 seconds timeout.")
        sys.exit(1)
        
    print("\n================== VALIDATION SUCCESS ==================")
    print(f"Message ID: {message_found.id}")
    print(f"Campaign ID: {message_found.campaign_id}")
    print(f"Lead ID: {message_found.lead_id}")
    print(f"Channel: {message_found.channel}")
    print(f"Recipient: {message_found.recipient_address}")
    print(f"Sequence Number: {message_found.sequence_number}")
    print(f"Status: {message_found.status}")
    print(f"Sent At: {message_found.sent_at}")
    print("------------------ Message Content ------------------")
    print(message_found.content)
    print("========================================================\n")
    print("[PASS] E2E Campaign Runner Validation completed successfully!")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
