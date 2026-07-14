import os

os.environ["GYM_DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["GYM_BOOTSTRAP_ADMIN"] = "false"
os.environ["GYM_TRUST_PROXY_AUTH"] = "false"
os.environ["GYM_COOKIE_SECURE"] = "false"
os.environ["GYM_ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1"
os.environ["GYM_PUBLIC_URL"] = "http://testserver"

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.main import app
from app.models import Base, User


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add(
            User(
                username="pulgaa",
                password_hash=hash_password("correct-horse-battery-staple"),
                timezone="Africa/Tunis",
            )
        )
        db.commit()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    # Requests do not need the production bootstrap lifespan: this fixture
    # creates the schema and account explicitly above.
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as test_client:
        yield test_client


@pytest.fixture
async def authenticated_client(client: AsyncClient) -> AsyncClient:
    response = await client.post(
        "/api/auth/login",
        json={"username": "pulgaa", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    return client
