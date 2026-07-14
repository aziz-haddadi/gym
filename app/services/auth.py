from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings
from app.core.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)
from app.models.session import AuthSession
from app.models.user import User
from app.services.exceptions import AuthenticationError, InputError


class AuthService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def bootstrap_admin(self) -> None:
        if not self.settings.bootstrap_admin:
            return

        username = self.settings.admin_username.strip().lower()
        existing = self.get_user_by_username(username)
        if existing:
            return

        try:
            ZoneInfo(self.settings.admin_timezone)
        except ZoneInfoNotFoundError as exc:
            raise RuntimeError(f"Unknown admin timezone: {self.settings.admin_timezone}") from exc

        password = self.settings.admin_password
        if len(password) < 12:
            raise RuntimeError("The initial admin password must contain at least 12 characters")

        self.db.add(
            User(
                username=username,
                password_hash=hash_password(password),
                timezone=self.settings.admin_timezone,
            )
        )
        try:
            self.db.commit()
        except IntegrityError:
            # Multiple web workers can bootstrap concurrently on the first run.
            self.db.rollback()
            if not self.get_user_by_username(username):
                raise

    def get_user_by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(User.username == username.strip().lower()))

    def login(self, username: str, password: str) -> tuple[User, str, datetime]:
        user = self.get_user_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password")

        raw_token = new_session_token()
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.session_days)
        self.db.add(
            AuthSession(
                user_id=user.id,
                token_hash=hash_session_token(raw_token),
                expires_at=expires_at,
            )
        )
        self.db.commit()
        return user, raw_token, expires_at

    def authenticate_session(self, raw_token: str | None) -> User:
        if not raw_token:
            raise AuthenticationError("Authentication required")
        now = datetime.now(UTC)
        session = self.db.scalar(
            select(AuthSession)
            .options(joinedload(AuthSession.user))
            .where(
                AuthSession.token_hash == hash_session_token(raw_token),
                AuthSession.expires_at > now,
            )
        )
        if not session:
            raise AuthenticationError("Session expired or invalid")
        last_seen = session.last_seen_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=UTC)
        if last_seen < now - timedelta(hours=1):
            session.last_seen_at = now
            self.db.commit()
        return session.user

    def logout(self, raw_token: str | None) -> None:
        if raw_token:
            self.db.execute(
                delete(AuthSession).where(AuthSession.token_hash == hash_session_token(raw_token))
            )
            self.db.commit()

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")
        if len(new_password) < 12:
            raise InputError("New password must contain at least 12 characters")
        if verify_password(new_password, user.password_hash):
            raise InputError("New password must be different")

        user.password_hash = hash_password(new_password)
        self.db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
        self.db.commit()

    def prune_expired_sessions(self) -> None:
        self.db.execute(delete(AuthSession).where(AuthSession.expires_at <= datetime.now(UTC)))
        self.db.commit()
