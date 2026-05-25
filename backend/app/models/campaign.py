import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.lead import Lead
    from app.models.message import Message


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"


class CampaignLanguage(str, enum.Enum):
    ru = "ru"
    kz = "kz"
    en = "en"


campaign_leads = Table(
    "campaign_leads",
    Base.metadata,
    Column("campaign_id", UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("lead_id", UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True),
)


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        Index("ix_campaigns_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status"),
        nullable=False,
        default=CampaignStatus.draft,
    )
    tone: Mapped[str] = mapped_column(String(50), nullable=False, default="professional")
    language: Mapped[CampaignLanguage] = mapped_column(
        Enum(CampaignLanguage, name="campaign_language"),
        nullable=False,
        default=CampaignLanguage.ru,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship("User", back_populates="campaigns")
    leads: Mapped[list["Lead"]] = relationship(
        "Lead", secondary="campaign_leads", back_populates="campaigns"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="campaign"
    )
