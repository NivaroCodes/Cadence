import asyncio
import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directory to path to support imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.gmail_credential import GmailCredential
from app.services.encryption import decrypt_token
from app.services.email_service import GmailService
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
    print("================== STARTING COMPREHENSIVE GMAIL OAUTH TESTS ==================")
    test_email = f"oauth_test_{uuid.uuid4().hex[:6]}@cadence.kz"
    test_password = "SecurePassword123!"
    
    # Create temporary user in DB for testing
    async with AsyncSessionLocal() as db:
        test_user = User(
            email=test_email,
            hashed_password="hashed_placeholder_value",
            is_active=True
        )
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        user_id = test_user.id
        jwt_token = create_jwt_token(user_id)

    print(f"[OK] Setup temporary test User: {test_email} (ID: {user_id})")

    # Mocks for Google API calls
    mock_token_data = {
        "access_token": "mock_google_access_token_12345",
        "refresh_token": "mock_google_refresh_token_67890",
        "expires_in": 3600
    }
    
    mock_gmail_profile = {
        "emailAddress": "connected_google_user@gmail.com"
    }

    # We patch the google oauth exchange, discovery build, and credentials refresh logic
    with patch("app.routers.oauth.exchange_code_for_token", new_callable=AsyncMock) as mock_exchange, \
         patch("app.routers.oauth.build") as mock_build_oauth, \
         patch("app.services.email_service.build") as mock_build_service, \
         patch("google.oauth2.credentials.Credentials.refresh", return_value=None) as mock_refresh:

        # Configure Mocks
        mock_exchange.return_value = mock_token_data
        
        # Build profile mock for Callback
        mock_service_instance_oauth = MagicMock()
        mock_service_instance_oauth.users().getProfile(userId='me').execute.return_value = mock_gmail_profile
        mock_build_oauth.return_value = mock_service_instance_oauth

        # Build service mock for EmailService
        mock_service_instance_service = MagicMock()
        mock_build_service.return_value = mock_service_instance_service

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:

            # Test 1: Authorize Endpoint returns valid RedirectResponse containing state
            print("\nTest 1: Requesting authorize redirect URL...")
            res_auth = await client.get(f"/oauth/google/authorize?state={user_id}")
            assert res_auth.status_code == 307 or res_auth.status_code == 302
            redirect_url = res_auth.headers["location"]
            assert "accounts.google.com" in redirect_url
            assert f"state={user_id}" in redirect_url
            print(f"   [PASS] Redirect URL generated successfully: {redirect_url[:50]}...")

            # Test 2: Callback with invalid state returns 400
            print("\nTest 2: Callback with invalid state format...")
            res_bad_state = await client.get("/oauth/google/callback?code=mock_code&state=invalid_uuid_format")
            assert res_bad_state.status_code == 400
            assert "State mismatch" in res_bad_state.json()["detail"]
            print("   [PASS] Invalid state correctly rejected with 400.")

            # Test 3: Successful Callback (exchange code, fetch profile, encrypt & store token)
            print("\nTest 3: Executing successful callback OAuth exchange...")
            res_callback = await client.get(f"/oauth/google/callback?code=mock_code&state={user_id}")
            assert res_callback.status_code == 200
            data_callback = res_callback.json()
            assert data_callback["user_id"] == str(user_id)
            assert data_callback["gmail_email"] == "connected_google_user@gmail.com"
            assert data_callback["status"] == "connected"
            print("   [PASS] OAuth callback exchanged successfully and returned connection status.")

            # Test 4: Verify encrypted storage of refresh_token in database
            print("\nTest 4: Verifying database credentials encryption...")
            async with AsyncSessionLocal() as db:
                stmt = select(GmailCredential).where(GmailCredential.user_id == user_id)
                res_cred = await db.execute(stmt)
                cred = res_cred.scalars().first()
                
                assert cred is not None
                assert cred.email == "connected_google_user@gmail.com"
                
                # The stored token in database MUST NOT equal the plain text refresh token
                assert cred.token != "mock_google_refresh_token_67890"
                print("   [PASS] Token stored in DB is verified to be ENCRYPTED (Not plaintext).")
                
                # Decrypting it must return the original refresh token
                decrypted = decrypt_token(cred.token, user_id)
                assert decrypted == "mock_google_refresh_token_67890"
                print("   [PASS] Decryption utility correctly resolves the plaintext refresh token.")

            # Test 5: Verify get_status endpoint matches connected status
            print("\nTest 5: Validating get_status endpoint...")
            headers = {"Authorization": f"Bearer {jwt_token}"}
            res_status = await client.get("/oauth/google/status", headers=headers)
            assert res_status.status_code == 200
            assert res_status.json()["connected"] is True
            assert res_status.json()["email"] == "connected_google_user@gmail.com"
            print("   [PASS] Get status returned connected status correctly.")

            # Test 6: Verify get_user_access_token / GmailService loads, decrypts and refreshes credentials
            print("\nTest 6: Validating GmailService user-specific credentials load and refresh...")
            gmail_service = GmailService(user_id=user_id)
            creds = await gmail_service._load_credentials_async()
            assert creds.refresh_token == "mock_google_refresh_token_67890"
            assert mock_refresh.call_count == 1
            print("   [PASS] GmailService decrypted, loaded, and successfully triggered access token refresh.")

            # Test 7: Verify disconnect endpoint removes credentials from database
            print("\nTest 7: Validating disconnect credentials removal...")
            res_disc = await client.post("/oauth/google/disconnect", headers=headers)
            assert res_disc.status_code == 200
            assert res_disc.json()["status"] == "disconnected"
            
            async with AsyncSessionLocal() as db:
                stmt_check = select(GmailCredential).where(GmailCredential.user_id == user_id)
                res_check = await db.execute(stmt_check)
                cred_check = res_check.scalars().first()
                assert cred_check is None
            print("   [PASS] Disconnect successfully deleted the credentials from PostgreSQL database.")

            # Test 8: Verify get_status endpoint returns disconnected after deletion
            print("\nTest 8: Validating get_status endpoint after disconnection...")
            res_status_disc = await client.get("/oauth/google/status", headers=headers)
            assert res_status_disc.status_code == 200
            assert res_status_disc.json()["connected"] is False
            assert res_status_disc.json()["email"] is None
            print("   [PASS] Get status correctly reported disconnected.")

            # Test 9: Verify user can reconnect credentials successfully
            print("\nTest 9: Testing user reconnection flow...")
            res_reconnect = await client.get(f"/oauth/google/callback?code=reconnect_code&state={user_id}")
            assert res_reconnect.status_code == 200
            assert res_reconnect.json()["status"] == "connected"
            
            async with AsyncSessionLocal() as db:
                stmt_reconn = select(GmailCredential).where(GmailCredential.user_id == user_id)
                res_reconn = await db.execute(stmt_reconn)
                cred_reconn = res_reconn.scalars().first()
                assert cred_reconn is not None
                assert cred_reconn.email == "connected_google_user@gmail.com"
            print("   [PASS] Reconnection succeeded and correctly populated DB.")

    # Cleanup temporary test user
    print("\nCleaning up test user records...")
    await cleanup_user(test_email)
    
    print("[SUCCESS] All Google OAuth and Encryption tests passed perfectly!")
    print("==============================================================================")


if __name__ == "__main__":
    asyncio.run(main())
