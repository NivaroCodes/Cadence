import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


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

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
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
    # 1 = initial touch, 2 = follow-up 1, 3 = follow-up 2
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    campaign: Mapped["Campaign"] = relationship(  # noqa: F821
        "Campaign", back_populates="messages"
    )
    lead: Mapped["Lead"] = relationship(  # noqa: F821
        "Lead", back_populates="messages"
    )
