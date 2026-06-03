import logging
from typing import Annotated, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.message import Message
from app.models.user import User
from app.dependencies import get_current_user
from app.schemas import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("", response_model=list[MessageResponse])
async def list_messages(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Any:
    stmt = (
        select(Message)
        .where(Message.user_id == current_user.id)
        .order_by(Message.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
