import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

# Add parent directory to path to support imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import AsyncClient
from jose import jwt
from sqlalchemy import select

from app.main import app
from app.database import AsyncSessionLocal
from app.models.user import User
from app.config import settings
from app.security import create_jwt_token


async def cleanup_user(email: str) -> None:
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.email == email)
        res = await db.execute(stmt)
        user = res.scalars().first()
        if user:
            await db.delete(user)
            await db.commit()


async def main() -> None:
    print("================== STARTING COMPREHENSIVE AUTH TESTS ==================")
    test_email = f"auth_test_{uuid.uuid4().hex[:6]}@cadence.kz"
    test_password = "SecurePassword123!"
    
    # Ensure starting in clean state
    await cleanup_user(test_email)
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        # Test 1: Signup Success
        print("\nTest 1: Signup new user...")
        signup_payload = {
            "email": test_email,
            "password": test_password,
            "company_name": "Test Company"
        }
        res_signup = await client.post("/auth/signup", json=signup_payload)
        assert res_signup.status_code == 201, f"Signup failed: {res_signup.text}"
        data_signup = res_signup.json()
        assert "jwt_token" in data_signup
        token_signup = data_signup["jwt_token"]
        print(f"   [PASS] Signup successful. Token issued: {token_signup[:20]}...")

        # Test 2: Duplicate email signup returns 400
        print("\nTest 2: Duplicate email signup failure...")
        res_dup = await client.post("/auth/signup", json=signup_payload)
        assert res_dup.status_code == 400
        assert "already exists" in res_dup.json()["detail"]
        print("   [PASS] Duplicate signup correctly blocked with 400 Bad Request.")

        # Test 3: Login Success
        print("\nTest 3: Login with correct credentials...")
        login_payload = {
            "email": test_email,
            "password": test_password
        }
        res_login = await client.post("/auth/login", json=login_payload)
        assert res_login.status_code == 200
        data_login = res_login.json()
        assert "jwt_token" in data_login
        token_login = data_login["jwt_token"]
        print(f"   [PASS] Login successful. Token issued: {token_login[:20]}...")

        # Test 4: Login failure with wrong password
        print("\nTest 4: Login with wrong password...")
        bad_login_payload = {
            "email": test_email,
            "password": "WrongPassword1!"
        }
        res_bad_login = await client.post("/auth/login", json=bad_login_payload)
        assert res_bad_login.status_code == 401
        assert "Incorrect email" in res_bad_login.json()["detail"]
        print("   [PASS] Wrong password correctly rejected with 401 Unauthorized.")

        # Test 5: get_current_user middleware validation (via /health which we can protect as an E2E check)
        print("\nTest 5: Validating get_current_user extraction...")
        # Decode the token and verify user_id subject matches DB
        payload = jwt.decode(token_login, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id_str = payload.get("sub")
        
        async with AsyncSessionLocal() as db:
            stmt = select(User).where(User.id == uuid.UUID(user_id_str))
            res_db = await db.execute(stmt)
            db_user = res_db.scalars().first()
            assert db_user is not None
            assert db_user.email == test_email
        print(f"   [PASS] JWT decrypted and correctly matched DB User ID: {user_id_str}")

        # Test 6: Invalid token returns 401
        print("\nTest 6: Invalid token verification...")
        res_invalid = await client.get("/health", headers={"Authorization": "Bearer invalid_token_value"})
        # Wait, health check route is currently public in main.py, let's verify if we hit health or another route
        # Let's test with a fake route that requires dependencies, or a dummy protected endpoint we will add in test.
        # Wait! To test dependencies.py get_current_user directly, we can invoke it programmatically!
        from fastapi.security import HTTPAuthorizationCredentials
        from app.dependencies import get_current_user
        
        # Test direct get_current_user call with valid token
        async with AsyncSessionLocal() as db:
            valid_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_login)
            current_user = await get_current_user(token=valid_creds, db=db)
            assert current_user.email == test_email
            print("   [PASS] get_current_user successfully returns User model for valid credentials.")

            # Test invalid token raises HTTP 401
            try:
                invalid_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad_token")
                await get_current_user(token=invalid_creds, db=db)
                print("   [FAIL] get_current_user did not raise exception for bad token!")
                sys.exit(1)
            except Exception as e:
                # Expect HTTPException 401
                assert hasattr(e, "status_code") and e.status_code == 401
                print("   [PASS] get_current_user correctly raises 401 HTTPException for invalid token.")

        # Test 7: Expired token returns 401
        print("\nTest 7: Expired token verification...")
        # Forge an expired token (by setting exp to -10 minutes)
        expired_exp = datetime.now(timezone.utc) - timedelta(minutes=10)
        expired_payload = {
            "sub": user_id_str,
            "exp": int(expired_exp.timestamp()),
        }
        expired_token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        
        async with AsyncSessionLocal() as db:
            try:
                expired_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=expired_token)
                await get_current_user(token=expired_creds, db=db)
                print("   [FAIL] get_current_user did not raise exception for expired token!")
                sys.exit(1)
            except Exception as e:
                assert hasattr(e, "status_code") and e.status_code == 401
                print("   [PASS] get_current_user correctly raises 401 HTTPException for expired token.")

        # Test 8: Refresh Token Success
        print("\nTest 8: Token refresh flow...")
        refresh_payload = {
            "refresh_token": token_login
        }
        res_refresh = await client.post("/auth/refresh", json=refresh_payload)
        assert res_refresh.status_code == 200
        data_refresh = res_refresh.json()
        assert "jwt_token" in data_refresh
        print(f"   [PASS] Token successfully refreshed. New token: {data_refresh['jwt_token'][:20]}...")

        # Test 9: Logout Endpoint
        print("\nTest 9: Logout endpoint check...")
        res_logout = await client.post("/auth/logout")
        assert res_logout.status_code == 200
        assert res_logout.json()["message"] == "logged out"
        print("   [PASS] Logout endpoint responded with success.")

    # Cleanup test data to keep staging DB pristine
    print("\nCleaning up test user...")
    await cleanup_user(test_email)
    print("[SUCCESS] All auth tests passed perfectly! Database cleaned up cleanly.")
    print("=========================================================================")


if __name__ == "__main__":
    asyncio.run(main())
