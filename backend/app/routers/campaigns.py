import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.campaign import Campaign, CampaignStatus
from app.models.lead import Lead
from app.schemas import CampaignCreate, CampaignResponse, CampaignUpdate
from app.services.campaign_runner import CampaignRunner

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_in: CampaignCreate, db: AsyncSession = Depends(get_db)
) -> Any:
    db_campaign = Campaign(
        name=campaign_in.name,
        description=campaign_in.description,
        tone=campaign_in.tone,
        language=campaign_in.language,
    )
    
    if campaign_in.lead_ids:
        stmt = select(Lead).where(Lead.id.in_(campaign_in.lead_ids))
        result = await db.execute(stmt)
        leads = list(result.scalars().all())
        if len(leads) != len(campaign_in.lead_ids):
            logger.warning("Some lead IDs provided were not found.")
        db_campaign.leads = leads

    db.add(db_campaign)
    try:
        await db.commit()
        await db.refresh(db_campaign)
        stmt = select(Campaign).options(selectinload(Campaign.leads)).where(Campaign.id == db_campaign.id)
        result = await db.execute(stmt)
        db_campaign = result.scalars().first()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error."
        )
        
    db_campaign.lead_count = len(db_campaign.leads)
    response_data = CampaignResponse.model_validate(db_campaign)
    return response_data


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Any:
    stmt = (
        select(Campaign)
        .options(selectinload(Campaign.leads))
        .order_by(Campaign.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    campaigns = result.scalars().all()
    
    responses = []
    for c in campaigns:
        c.lead_count = len(c.leads)
        resp = CampaignResponse.model_validate(c)
        responses.append(resp)
    return responses


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(Campaign).options(selectinload(Campaign.leads)).where(Campaign.id == campaign_id)
    result = await db.execute(stmt)
    db_campaign = result.scalars().first()
    
    if not db_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        
    db_campaign.lead_count = len(db_campaign.leads)
    response_data = CampaignResponse.model_validate(db_campaign)
    return response_data


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: uuid.UUID, campaign_in: CampaignUpdate, db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(Campaign).options(selectinload(Campaign.leads)).where(Campaign.id == campaign_id)
    result = await db.execute(stmt)
    db_campaign = result.scalars().first()
    
    if not db_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    update_data = campaign_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_campaign, field, value)

    try:
        await db.commit()
        await db.refresh(db_campaign)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error."
        )
        
    db_campaign.lead_count = len(db_campaign.leads)
    response_data = CampaignResponse.model_validate(db_campaign)
    return response_data


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    result = await db.execute(stmt)
    db_campaign = result.scalars().first()
    
    if not db_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    await db.delete(db_campaign)
    await db.commit()


@router.post("/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign(
    campaign_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(Campaign).options(selectinload(Campaign.leads)).where(Campaign.id == campaign_id)
    result = await db.execute(stmt)
    db_campaign = result.scalars().first()
    
    if not db_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        
    if db_campaign.status == CampaignStatus.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign is already active")
        
    db_campaign.status = CampaignStatus.active
    if not db_campaign.started_at:
        db_campaign.started_at = datetime.now(timezone.utc)
        
    await db.commit()
    await db.refresh(db_campaign)
    
    background_tasks.add_task(CampaignRunner().run_campaign, db_campaign.id)
    
    db_campaign.lead_count = len(db_campaign.leads)
    response_data = CampaignResponse.model_validate(db_campaign)
    return response_data


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(Campaign).options(selectinload(Campaign.leads)).where(Campaign.id == campaign_id)
    result = await db.execute(stmt)
    db_campaign = result.scalars().first()
    
    if not db_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        
    if db_campaign.status != CampaignStatus.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only active campaigns can be paused")
        
    db_campaign.status = CampaignStatus.paused
    await db.commit()
    await db.refresh(db_campaign)
    
    db_campaign.lead_count = len(db_campaign.leads)
    response_data = CampaignResponse.model_validate(db_campaign)
    return response_data


@router.get("/{campaign_id}/stats")
async def campaign_stats(
    campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    stmt = select(Campaign).options(selectinload(Campaign.leads)).where(Campaign.id == campaign_id)
    result = await db.execute(stmt)
    db_campaign = result.scalars().first()
    
    if not db_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        
    return {
        "campaign_id": str(db_campaign.id),
        "status": db_campaign.status.value,
        "total_leads": len(db_campaign.leads),
        "messages_sent": 0,
        "replies_received": 0,
    }
