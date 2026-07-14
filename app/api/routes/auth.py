from typing import Annotated

from fastapi import APIRouter, Cookie, Response, status

from app.api.dependencies import (
    COOKIE_NAME,
    AppSettings,
    CurrentUser,
    Database,
)
from app.schemas.auth import LoginRequest, PasswordChangeRequest, UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=UserRead)
def login(data: LoginRequest, response: Response, db: Database, settings: AppSettings) -> UserRead:
    user, token, _ = AuthService(db, settings).login(data.username, data.password)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.session_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )
    return UserRead.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Database,
    settings: AppSettings,
    session_cookie: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> Response:
    AuthService(db, settings).logout(session_cookie)
    response.delete_cookie(COOKIE_NAME, path="/", secure=settings.cookie_secure, samesite="strict")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: PasswordChangeRequest,
    response: Response,
    user: CurrentUser,
    db: Database,
    settings: AppSettings,
) -> Response:
    AuthService(db, settings).change_password(user, data.current_password, data.new_password)
    response.delete_cookie(COOKIE_NAME, path="/", secure=settings.cookie_secure, samesite="strict")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
