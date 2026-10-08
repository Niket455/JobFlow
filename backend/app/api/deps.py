import uuid
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.adapters.base import Fetcher
from app.adapters.user_url import build_fetcher
from app.core.db import get_db
from app.core.security import decode_token
from app.core.storage import ObjectStorage, build_storage
from app.email.base import EmailSender
from app.email.factory import build_email_sender
from app.gateway.factory import build_gateway
from app.gateway.gateway import LLMGateway
from app.models.user import User
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


@lru_cache
def get_storage() -> ObjectStorage:
    return build_storage()


@lru_cache
def get_gateway() -> LLMGateway:
    return build_gateway()


@lru_cache
def get_fetcher() -> Fetcher:
    return build_fetcher()


@lru_cache
def get_email_sender() -> EmailSender:
    return build_email_sender()


StorageDep = Annotated[ObjectStorage, Depends(get_storage)]
GatewayDep = Annotated[LLMGateway, Depends(get_gateway)]
FetcherDep = Annotated[Fetcher, Depends(get_fetcher)]
EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender)]
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def get_current_user(db: DbSession, credentials: Credentials) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = decode_token(credentials.credentials)
        user_id = uuid.UUID(str(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise unauthorized from exc
    if payload.get("type") != "access":
        raise unauthorized
    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
