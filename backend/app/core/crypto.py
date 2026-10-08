from cryptography.fernet import Fernet

from app.core.config import settings


def _master_fernet() -> Fernet:
    return Fernet(settings.master_key.encode())


def generate_data_key() -> str:
    """A fresh per-user data key (urlsafe base64, as Fernet expects)."""
    return Fernet.generate_key().decode()


def wrap_data_key(data_key: str) -> str:
    """Encrypt a user's data key with the master key for storage at rest."""
    return _master_fernet().encrypt(data_key.encode()).decode()


def unwrap_data_key(wrapped_data_key: str) -> str:
    return _master_fernet().decrypt(wrapped_data_key.encode()).decode()


def encrypt_text(data_key: str, plaintext: str) -> str:
    return Fernet(data_key.encode()).encrypt(plaintext.encode()).decode()


def decrypt_text(data_key: str, token: str) -> str:
    return Fernet(data_key.encode()).decrypt(token.encode()).decode()
