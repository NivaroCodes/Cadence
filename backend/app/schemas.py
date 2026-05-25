import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, HttpUrl, Field

from app.models.campaign import CampaignLanguage, CampaignStatus


class LeadBase(BaseModel):
    name: str
    company: str
    email: EmailStr
    phone: str | None = None
    linkedin_url: HttpUrl | str | None = None
    website: HttpUrl | str | None = None
    industry: str | None = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    name: str | None = None
    company: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    linkedin_url: HttpUrl | str | None = None
    website: HttpUrl | str | None = None
    industry: str | None = None


class LeadResponse(LeadBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignBase(BaseModel):
    name: str
    description: str | None = None
    tone: Literal["professional", "casual", "friendly"] = "professional"
    language: CampaignLanguage = CampaignLanguage.ru


class CampaignCreate(CampaignBase):
    lead_ids: list[uuid.UUID] = Field(default_factory=list)


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tone: Literal["professional", "casual", "friendly"] | None = None
    language: CampaignLanguage | None = None


class CampaignResponse(CampaignBase):
    id: uuid.UUID
    status: CampaignStatus
    lead_count: int
    created_at: datetime
    started_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    company_name: str | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    jwt_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str
