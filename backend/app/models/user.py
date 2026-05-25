import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.lead import Lead
    from app.models.message import Message
    from app.models.gmail_credential import GmailCredential
    from app.models.api_key import ApiKey


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    campaigns: Mapped[list["Campaign"]] = relationship("Campaign", back_populates="user", cascade="all, delete-orphan")
    leads: Mapped[list["Lead"]] = relationship("Lead", back_populates="user", cascade="all, delete-orphan")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    gmail_credentials: Mapped[list["GmailCredential"]] = relationship("GmailCredential", back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[list["ApiKey"]] = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
