import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.campaign import Campaign
    from app.models.lead import Lead


class MessageChannel(str, enum.Enum):
    email = "email"
    telegram = "telegram"


class MessageStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    opened = "opened"
    replied = "replied"
    bounced = "bounced"


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_campaign_lead_seq", "campaign_id", "lead_id", "sequence_number"),
        Index("ix_messages_user_created_at", "user_id", "created_at"),
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
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[MessageChannel] = mapped_column(
        Enum(MessageChannel, name="message_channel"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus, name="message_status"),
        nullable=False,
        default=MessageStatus.draft,
    )
    recipient_address: Mapped[str] = mapped_column(String(500), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reply_check_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="messages")
    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="messages"
    )
    lead: Mapped["Lead"] = relationship(
        "Lead", back_populates="messages"
    )
