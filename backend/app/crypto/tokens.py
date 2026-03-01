"""Token encryption/decryption helpers."""
from cryptography.fernet import Fernet

from app.config import settings


fernet = Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())


def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    return fernet.decrypt(encrypted_token.encode()).decode()
