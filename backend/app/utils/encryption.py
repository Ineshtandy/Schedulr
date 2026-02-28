"""Token encryption utilities using Fernet symmetric encryption."""
from cryptography.fernet import Fernet
from app.config import settings


# Initialize Fernet cipher with encryption key from settings
cipher = Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_token(token: str) -> str:
    """Encrypt a token string.
    
    Args:
        token: Plain text token to encrypt
        
    Returns:
        Encrypted token as base64 string
    """
    return cipher.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted token.
    
    Args:
        encrypted_token: Encrypted token as base64 string
        
    Returns:
        Decrypted plain text token
        
    Raises:
        InvalidToken: If token cannot be decrypted
    """
    return cipher.decrypt(encrypted_token.encode()).decode()
