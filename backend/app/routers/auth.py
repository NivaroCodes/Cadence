import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas import UserCreate, TokenResponse, LoginRequest, TokenRefreshRequest
from app.security import hash_password, verify_password, create_jwt_token, verify_jwt_token
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == payload.email)
    res = await db.execute(stmt)
    if res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    new_user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    token = create_jwt_token(new_user.id, expires_hours=settings.JWT_EXPIRATION_HOURS)
    return TokenResponse(
        jwt_token=token,
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == payload.email)
    res = await db.execute(stmt)
    user = res.scalars().first()
    
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
        
    token = create_jwt_token(user.id, expires_hours=settings.JWT_EXPIRATION_HOURS)
    return TokenResponse(
        jwt_token=token,
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: TokenRefreshRequest):
    token_payload = verify_jwt_token(payload.refresh_token)
    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
        
    user_id_str = token_payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
        
    new_token = create_jwt_token(uuid.UUID(user_id_str), expires_hours=settings.JWT_EXPIRATION_HOURS)
    return TokenResponse(
        jwt_token=new_token,
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600
    )


@router.post("/logout")
async def logout():
    return {"message": "logged out"}
