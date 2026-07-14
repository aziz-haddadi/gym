from typing import Annotated

from fastapi import Cookie, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.user import User
from app.services.auth import AuthService
from app.services.exceptions import AuthenticationError

COOKIE_NAME = "gym_session"

Database = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_current_user(
    request: Request,
    db: Database,
    settings: AppSettings,
    session_cookie: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> User:
    auth = AuthService(db, settings)
    if settings.trust_proxy_auth:
        username = request.headers.get(settings.proxy_auth_header)
        if not username:
            raise AuthenticationError("Reverse-proxy authentication required")
        user = auth.get_user_by_username(username)
        if not user:
            raise AuthenticationError("Authenticated proxy user is not configured in the app")
        return user
    return auth.authenticate_session(session_cookie)


CurrentUser = Annotated[User, Depends(get_current_user)]
