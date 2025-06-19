import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

from ..database import db
from ..security import encrypt_data, decrypt_data
from ..auth.authentication import create_access_token, JWT_SECRET_KEY, ALGORITHM

router = APIRouter(
    tags=["authentication"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/google/login")

class AuthCodeRequest(BaseModel):
    code: str

class ClientConfig(BaseModel):
    google_client_id: str

class GoogleLoginRequest(BaseModel):
    token: str # This is the Google ID token

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Decodes the JWT token to get the current user's ID.
    This function will be used as a dependency for protected endpoints.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # You could fetch the user document from Firestore here if needed,
    # but for now, just returning the ID is sufficient.
    return {"uid": user_id}

@router.post("/api/auth/google/login")
async def google_login(request: GoogleLoginRequest):
    """
    Handles Google Sign-In. Verifies Google token, finds or creates a user,
    and returns an internal access token.
    """
    try:
        # Verify the ID token with Google
        idinfo = id_token.verify_oauth2_token(
            request.token,
            google_requests.Request(),
            os.getenv("GOOGLE_CLIENT_ID")
        )

        user_id = idinfo['sub']
        user_email = idinfo.get('email')
        user_name = idinfo.get('name')

        # Check if user exists in our database
        user_doc_ref = db.collection('users').document(user_id)
        user_doc = await user_doc_ref.get()

        if not user_doc.exists:
            # Create new user
            await user_doc_ref.set({
                'email': user_email,
                'name': user_name,
                'created_at': datetime.utcnow()
            })

        # Create our own internal access token
        access_token = create_access_token(data={"sub": user_id})

        return {"access_token": access_token, "token_type": "bearer"}

    except ValueError as e:
        # Invalid token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"Error during Google login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login."
        )

@router.get("/api/config", response_model=ClientConfig)
async def get_client_config():
    """
    Provides the client-side application with necessary configuration,
    such as the Google Client ID for the OAuth flow.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    print(f"🛠️ [CONFIG] Providing Google Client ID to frontend: {client_id}")
    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID is not set in the environment.")

    return ClientConfig(
        google_client_id=client_id
    )

@router.post("/api/oauth/exchange-code")
async def exchange_code(request: AuthCodeRequest, current_user: dict = Depends(get_current_user)):
    """
    Exchanges a Google OAuth authorization code for credentials and stores them securely.
    Requires our internal JWT authentication.
    """
    user_id = current_user.get("uid")
    
    try:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise ValueError("Google Client ID or Secret is not configured on the server.")

        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=['https://www.googleapis.com/auth/youtube.readonly'],
            redirect_uri='postmessage'
        )

        # Exchange the authorization code for credentials
        flow.fetch_token(code=request.code)
        creds = flow.credentials

        # Convert credentials to a dict and encrypt them
        creds_json = creds.to_json()
        encrypted_creds = encrypt_data(creds_json.encode())

        # Save encrypted credentials to Firestore
        cred_doc_ref = db.collection("user_credentials").document(user_id)
        await cred_doc_ref.set({"credentials": encrypted_creds})

        return {"message": "Successfully connected YouTube account."}

    except Exception as e:
        import traceback
        print(f"Error exchanging code for user {user_id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to exchange authorization code."
        )

@router.get("/api/auth/youtube/status")
async def get_youtube_auth_status(current_user: dict = Depends(get_current_user)):
    """
    Checks if the current user has valid YouTube credentials stored.
    """
    user_id = current_user.get("uid")
    cred_doc = await db.collection("user_credentials").document(user_id).get()
    
    if cred_doc.exists:
        return {"isConnected": True}
    
    return {"isConnected": False} 