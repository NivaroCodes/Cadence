# Cadence API Endpoint Validation & Test Results

**Date / Time of Test Run:** 2026-05-22T13:49:48+05:00 (Local Time) / 2026-05-22T08:49:48Z (UTC)  
**Database Host:** Supabase PostgreSQL  
**Server Host:** Local FastAPI Server (uvicorn with `--log-level debug`)

---

## Executive Summary
All **8 CRUD endpoints** were tested sequentially on a live FastAPI instance. All endpoints executed successfully, returned the correct status codes, and mapped data from/to the Supabase DB perfectly. 

Two critical server crashes/bugs were diagnosed and resolved:
1. **SQLAlchemy Mapper Failure:** Exposing and importing all models dynamically in `app/models/__init__.py` to ensure mapper compilation works seamlessly on the first query.
2. **Pydantic Validation Error:** Assigning the calculated `lead_count` directly to the `Campaign` ORM model before executing `CampaignResponse.model_validate()` across all campaign endpoints.

---

## Sequential Test Results

| Step | Endpoint Tested | Status Code | Outcome | Timestamp (UTC) | Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **1** | `POST /api/v1/leads` | **201** | ✓ Work | `2026-05-22T08:49:28.343Z` | Lead "Nurlan Aitbayev" created successfully |
| **2** | `GET /api/v1/leads` | **200** | ✓ Work | `2026-05-22T08:49:30.686Z` | Listed active leads, verified lead exists |
| **3** | `GET /api/v1/leads/{id}` | **200** | ✓ Work | `2026-05-22T08:49:32.116Z` | Fetched single lead by UUID successfully |
| **4** | `POST /api/v1/campaigns` | **201** | ✓ Work | `2026-05-22T08:49:33.327Z` | Campaign "Kaspi Outreach Campaign" created with lead |
| **5** | `GET /api/v1/campaigns` | **200** | ✓ Work | `2026-05-22T08:49:37.401Z` | Listed campaigns, verified lead_count = 1 |
| **6** | `POST /api/v1/campaigns/{id}/start` | **200** | ✓ Work | `2026-05-22T08:49:38.644Z` | Started campaign (status transitions to `active`) |
| **7** | `POST /api/v1/campaigns/{id}/pause` | **200** | ✓ Work | `2026-05-22T08:49:42.628Z` | Paused campaign (status transitions to `paused`) |
| **8** | `GET /api/v1/campaigns/{id}/stats` | **200** | ✓ Work | `2026-05-22T08:49:46.018Z` | Fetched stats showing total_leads = 1, status = paused |

---

## Detailed Payload & Response Logs

### Step 1: POST /api/v1/leads
- **Payload:**
  ```json
  {
    "name": "Nurlan Aitbayev",
    "company": "Kaspi Bank",
    "email": "nurlan@kaspi.kz",
    "phone": "+77012345678",
    "linkedin_url": "https://linkedin.com/in/nurlan",
    "website": "https://kaspi.kz",
    "industry": "Finance"
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "name": "Nurlan Aitbayev",
    "company": "Kaspi Bank",
    "email": "nurlan@kaspi.kz",
    "phone": "+77012345678",
    "linkedin_url": "https://linkedin.com/in/nurlan",
    "website": "https://kaspi.kz",
    "industry": "Finance",
    "id": "f0a6446b-dc26-4cbe-bf37-5f9ac5e0693a",
    "created_at": "2026-05-22T08:49:32.547746Z"
  }
  ```

### Step 2: GET /api/v1/leads
- **Response (200 OK):**
  ```json
  [
    {
      "name": "Nurlan Aitbayev",
      "company": "Kaspi Bank",
      "email": "nurlan@kaspi.kz",
      "phone": "+77012345678",
      "linkedin_url": "https://linkedin.com/in/nurlan",
      "website": "https://kaspi.kz",
      "industry": "Finance",
      "id": "f0a6446b-dc26-4cbe-bf37-5f9ac5e0693a",
      "created_at": "2026-05-22T08:49:32.547746Z"
    }
  ]
  ```

### Step 3: GET /api/v1/leads/{id}
- **Response (200 OK):**
  ```json
  {
    "name": "Nurlan Aitbayev",
    "company": "Kaspi Bank",
    "email": "nurlan@kaspi.kz",
    "phone": "+77012345678",
    "linkedin_url": "https://linkedin.com/in/nurlan",
    "website": "https://kaspi.kz",
    "industry": "Finance",
    "id": "f0a6446b-dc26-4cbe-bf37-5f9ac5e0693a",
    "created_at": "2026-05-22T08:49:32.547746Z"
  }
  ```

### Step 4: POST /api/v1/campaigns
- **Payload:**
  ```json
  {
    "name": "Kaspi Outreach Campaign",
    "description": "Cold outreach to Kaspi Bank executives",
    "tone": "professional",
    "language": "ru",
    "lead_ids": ["f0a6446b-dc26-4cbe-bf37-5f9ac5e0693a"]
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "name": "Kaspi Outreach Campaign",
    "description": "Cold outreach to Kaspi Bank executives",
    "tone": "professional",
    "language": "ru",
    "id": "dcb7a9ed-a5e0-4889-8a5c-360e9411af1f",
    "status": "draft",
    "lead_count": 1,
    "created_at": "2026-05-22T08:49:37.558033Z",
    "started_at": null
  }
  ```

### Step 5: GET /api/v1/campaigns
- **Response (200 OK):**
  ```json
  [
    {
      "name": "Kaspi Outreach Campaign",
      "description": "Cold outreach to Kaspi Bank executives",
      "tone": "professional",
      "language": "ru",
      "id": "dcb7a9ed-a5e0-4889-8a5c-360e9411af1f",
      "status": "draft",
      "lead_count": 1,
      "created_at": "2026-05-22T08:49:37.558033Z",
      "started_at": null
    }
  ]
  ```

### Step 6: POST /api/v1/campaigns/{id}/start
- **Response (200 OK):**
  ```json
  {
    "name": "Kaspi Outreach Campaign",
    "description": "Cold outreach to Kaspi Bank executives",
    "tone": "professional",
    "language": "ru",
    "id": "dcb7a9ed-a5e0-4889-8a5c-360e9411af1f",
    "status": "active",
    "lead_count": 1,
    "created_at": "2026-05-22T08:49:37.558033Z",
    "started_at": "2026-05-22T08:49:40.270191Z"
  }
  ```

### Step 7: POST /api/v1/campaigns/{id}/pause
- **Response (200 OK):**
  ```json
  {
    "name": "Kaspi Outreach Campaign",
    "description": "Cold outreach to Kaspi Bank executives",
    "tone": "professional",
    "language": "ru",
    "id": "dcb7a9ed-a5e0-4889-8a5c-360e9411af1f",
    "status": "paused",
    "lead_count": 1,
    "created_at": "2026-05-22T08:49:37.558033Z",
    "started_at": "2026-05-22T08:49:40.270191Z"
  }
  ```

### Step 8: GET /api/v1/campaigns/{id}/stats
- **Response (200 OK):**
  ```json
  {
    "campaign_id": "dcb7a9ed-a5e0-4889-8a5c-360e9411af1f",
    "status": "paused",
    "total_leads": 1,
    "messages_sent": 0,
    "replies_received": 0
  }
  ```

---

## Resolved Errors & Fix Details

### 1. SQLAlchemy Mapper Failure
- **Error Message:** `sqlalchemy.exc.InvalidRequestError: When initializing mapper Mapper[Campaign(campaigns)], expression 'Message' failed to locate a name ('Message').`
- **Location:** `backend/app/models/campaign.py` relationship compiling.
- **Cause:** When starting FastAPI, only routers for `leads` and `campaigns` were loaded. Submodule `app.models.message` containing the `Message` class was never imported at runtime. Therefore, SQLAlchemy could not resolve the `"Message"` relationship name during compilation on the first database query.
- **Fix Applied:** Modified `backend/app/models/__init__.py` to import and expose all models:
  ```python
  from app.models.lead import Lead
  from app.models.campaign import Campaign, CampaignStatus, CampaignLanguage
  from app.models.message import Message, MessageChannel, MessageStatus
  
  __all__ = [
      "Lead",
      "Campaign",
      "CampaignStatus",
      "CampaignLanguage",
      "Message",
      "MessageChannel",
      "MessageStatus",
  ]
  ```

### 2. CampaignResponse Pydantic ValidationError
- **Error Message:** `pydantic_core._pydantic_core.ValidationError: 1 validation error for CampaignResponse: lead_count: Field required`
- **Location:** `backend/app/routers/campaigns.py` on all endpoints utilizing `CampaignResponse`.
- **Cause:** `CampaignResponse` schema requires a `lead_count` field (`lead_count: int`). The endpoints originally ran `response_data = CampaignResponse.model_validate(db_campaign)` and assigned the field afterwards. However, since the database ORM class `Campaign` has no `lead_count` column/attribute, `model_validate` instantly raised a Pydantic validation error before the next line of code could execute.
- **Fix Applied:** Modified all 6 campaign endpoints returning `CampaignResponse` to compute and assign `lead_count` directly to the database model object before validation:
  ```python
  db_campaign.lead_count = len(db_campaign.leads)
  response_data = CampaignResponse.model_validate(db_campaign)
  ```
