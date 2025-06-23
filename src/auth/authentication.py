import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

# This is the secret key for signing our application's JWTs.
# It is completely separate from the ENCRYPTION_KEY used for data encryption.
# You should generate this with `openssl rand -hex 32` and set it as an environment variable.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "a-silly-default-secret-key-for-dev")
print("JWT_SECRET_KEY from env:", os.getenv("JWT_SECRET_KEY"))

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # One week

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(object):
    """A placeholder for token data."""
    id: Optional[str] = None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a new JWT access token for our internal session."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "sub": str(data.get("sub"))}) # ensure sub is a string
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password, hashed_password):
    """Verifies a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Hashes a password."""
    return pwd_context.hash(password) 