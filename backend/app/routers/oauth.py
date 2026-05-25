import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.database import get_db
from app.models.user import User
from app.models.gmail_credential import GmailCredential
from app.dependencies import get_current_user
from app.services.google_oauth import get_google_oauth_url, exchange_code_for_token
from app.services.encryption import encrypt_token
from app.config import settings

router = APIRouter(prefix="/oauth", tags=["Google OAuth"])


@router.get("/google/authorize")
async def authorize(state: str):
    try:
        uuid.UUID(state)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter, must be a UUID"
        )
    auth_url = get_google_oauth_url(state)
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    try:
        user_id = uuid.UUID(state)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State mismatch or invalid state format"
        )

    # Verify user exists
    stmt_user = select(User).where(User.id == user_id)
    res_user = await db.execute(stmt_user)
    user = res_user.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Exchange authorization code for token dictionary
    try:
        token_data = await exchange_code_for_token(code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange authorization code: {str(e)}"
        )

    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve refresh token. Try removing Cadence from your Google Account settings and connecting again."
        )

    # Retrieve Gmail address from Gmail Profile API
    try:
        import asyncio
        creds = Credentials(
            token=token_data["access_token"],
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        service = build('gmail', 'v1', credentials=creds)
        profile = await asyncio.to_thread(service.users().getProfile(userId='me').execute)
        gmail_email = profile.get("emailAddress")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to retrieve Gmail profile: {str(e)}"
        )

    # Encrypt the refresh token
    encrypted_refresh_token = encrypt_token(refresh_token, user_id)

    # Upsert the Gmail credentials record (Unique user_id constraint enforced)
    stmt_cred = select(GmailCredential).where(GmailCredential.user_id == user_id)
    res_cred = await db.execute(stmt_cred)
    cred = res_cred.scalars().first()

    from sqlalchemy.sql import func
    if cred:
        cred.email = gmail_email
        cred.token = encrypted_refresh_token
        cred.connected_at = func.now()
    else:
        cred = GmailCredential(
            user_id=user_id,
            email=gmail_email,
            token=encrypted_refresh_token
        )
        db.add(cred)

    await db.commit()
    return {
        "user_id": str(user_id),
        "gmail_email": gmail_email,
        "status": "connected"
    }


@router.post("/google/disconnect")
async def disconnect(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(GmailCredential).where(GmailCredential.user_id == current_user.id)
    res = await db.execute(stmt)
    cred = res.scalars().first()

    if not cred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No connected Gmail credentials found to disconnect."
        )

    await db.delete(cred)
    await db.commit()
    return {"status": "disconnected"}


@router.get("/google/status")
async def get_status(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(GmailCredential).where(GmailCredential.user_id == current_user.id)
    res = await db.execute(stmt)
    cred = res.scalars().first()

    if cred:
        return {
            "connected": True,
            "email": cred.email
        }
    return {
        "connected": False,
        "email": None
    }


def sa_now_helper():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)
