from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, make_url


class Settings(BaseSettings):
    """Runtime configuration loaded from GYM_* environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="GYM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Gym Pulgaa"
    environment: str = "production"
    log_level: str = "INFO"
    public_url: str = "https://gym.pulgaa.xyz"
    allowed_hosts: str = "gym.pulgaa.xyz,localhost,127.0.0.1,testserver"
    cookie_secure: bool = True
    session_days: int = Field(default=30, ge=1, le=365)
    trust_proxy_auth: bool = True
    proxy_auth_header: str = "X-Gym-User"

    database_url: str | None = None
    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "gym"
    db_user: str = "gym_app"
    db_password_file: Path = Path("/run/secrets/postgres_app_password")
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=200)

    bootstrap_admin: bool = True
    admin_username: str = "pulgaa"
    admin_timezone: str = "Africa/Tunis"
    admin_password_file: Path = Path("/run/secrets/admin_password")

    @staticmethod
    def _read_secret(path: Path, label: str) -> str:
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"Unable to read {label} from {path}") from exc
        if not value:
            raise RuntimeError(f"{label} in {path} is empty")
        return value

    @property
    def sqlalchemy_url(self) -> URL:
        if self.database_url:
            return make_url(self.database_url)
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.db_user,
            password=self._read_secret(self.db_password_file, "database password"),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @property
    def admin_password(self) -> str:
        return self._read_secret(self.admin_password_file, "initial admin password")

    @property
    def host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @property
    def public_origin(self) -> str:
        parsed = urlparse(self.public_url)
        return f"{parsed.scheme}://{parsed.netloc}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
