import csv
import io
import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import EmailStr
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.lead import Lead
from app.models.user import User
from app.dependencies import get_current_user
from app.schemas import LeadCreate, LeadResponse, LeadUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_in: LeadCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    stmt = select(Lead).where(Lead.email == str(lead_in.email))
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lead with this email already exists."
        )

    db_lead = Lead(
        user_id=current_user.id,
        **lead_in.model_dump(exclude_unset=True, exclude_none=True)
    )
    if db_lead.linkedin_url:
        db_lead.linkedin_url = str(db_lead.linkedin_url)
    if db_lead.website:
        db_lead.website = str(db_lead.website)
        
    db.add(db_lead)
    try:
        await db.commit()
        await db.refresh(db_lead)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error."
        )
    return db_lead


@router.get("", response_model=list[LeadResponse])
async def list_leads(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Any:
    stmt = (
        select(Lead)
        .where(Lead.user_id == current_user.id)
        .order_by(Lead.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    stmt = select(Lead).where((Lead.id == lead_id) & (Lead.user_id == current_user.id))
    result = await db.execute(stmt)
    db_lead = result.scalars().first()
    if not db_lead:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return db_lead


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: uuid.UUID,
    lead_in: LeadUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    stmt = select(Lead).where(Lead.id == lead_id)
    result = await db.execute(stmt)
    db_lead = result.scalars().first()
    
    if not db_lead:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if db_lead.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    update_data = lead_in.model_dump(exclude_unset=True)
    if "email" in update_data:
        check_stmt = select(Lead).where(Lead.email == str(update_data["email"]), Lead.id != lead_id)
        check_res = await db.execute(check_stmt)
        if check_res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lead with this email already exists."
            )
        update_data["email"] = str(update_data["email"])

    if "linkedin_url" in update_data and update_data["linkedin_url"]:
        update_data["linkedin_url"] = str(update_data["linkedin_url"])
    if "website" in update_data and update_data["website"]:
        update_data["website"] = str(update_data["website"])

    for field, value in update_data.items():
        setattr(db_lead, field, value)

    try:
        await db.commit()
        await db.refresh(db_lead)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error."
        )
    return db_lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = select(Lead).where(Lead.id == lead_id)
    result = await db.execute(stmt)
    db_lead = result.scalars().first()
    
    if not db_lead:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if db_lead.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    await db.delete(db_lead)
    await db.commit()


@router.post("/import-csv", status_code=status.HTTP_200_OK)
async def import_leads_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    
    contents = await file.read()
    decoded = contents.decode("utf-8-sig")
    
    reader = csv.DictReader(io.StringIO(decoded))
    
    required_cols = {"name", "company", "email"}
    if not reader.fieldnames or not required_cols.issubset(set(reader.fieldnames)):
        raise HTTPException(
            status_code=400, 
            detail=f"CSV must contain at least the following columns: {', '.join(required_cols)}"
        )
        
    created_count = 0
    errors = []
    
    for row_idx, row in enumerate(reader, start=1):
        try:
            lead_in = LeadCreate(
                name=row.get("name", "").strip(),
                company=row.get("company", "").strip(),
                email=row.get("email", "").strip(),
                phone=row.get("phone", "").strip() or None,
                linkedin_url=row.get("linkedin_url", "").strip() or None,
                website=row.get("website", "").strip() or None,
                industry=row.get("industry", "").strip() or None,
            )
            
            stmt = select(Lead).where(Lead.email == str(lead_in.email))
            result = await db.execute(stmt)
            if result.scalars().first():
                errors.append(f"Row {row_idx}: Email '{lead_in.email}' already exists.")
                continue
                
            db_lead = Lead(
                user_id=current_user.id,
                **lead_in.model_dump(exclude_unset=True, exclude_none=True)
            )
            if db_lead.linkedin_url:
                db_lead.linkedin_url = str(db_lead.linkedin_url)
            if db_lead.website:
                db_lead.website = str(db_lead.website)
                
            db.add(db_lead)
            created_count += 1
            
        except Exception as e:
            logger.warning("Error processing CSV row %d: %s", row_idx, str(e))
            errors.append(f"Row {row_idx}: Validation error - {str(e)}")

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Database integrity error during bulk import.")
        
    return {
        "status": "success",
        "imported": created_count,
        "errors": errors
    }
