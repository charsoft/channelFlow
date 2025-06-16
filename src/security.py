import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# It's critical that this key is set in your environment.
# You can generate a new key using: from cryptography.fernet import Fernet; Fernet.generate_key()
ENCRYPTION_KEY = os.getenv("SECRET_KEY")

if not ENCRYPTION_KEY:
    raise ValueError("SECRET_KEY environment variable not set. Cannot perform encryption.")

f = Fernet(ENCRYPTION_KEY.encode())

def encrypt_data(data: bytes) -> bytes:
    """Encrypts data using Fernet."""
    return f.encrypt(data)

def decrypt_data(encrypted_data: bytes) -> bytes:
    """Decrypts data using Fernet."""
    return f.decrypt(encrypted_data) 