from app.core.crypto import generate_data_key, unwrap_data_key, wrap_data_key
from app.models.user import User
from app.repositories.user_repository import UserRepository


def ensure_data_key(user: User, users: UserRepository) -> str:
    """Return the user's data key, generating and persisting one on first use."""
    if user.wrapped_data_key:
        return unwrap_data_key(user.wrapped_data_key)
    data_key = generate_data_key()
    user.wrapped_data_key = wrap_data_key(data_key)
    users.db.commit()
    return data_key
