import os
import sys
from pathlib import Path
import pytest
import pytest_asyncio
import importlib
from bson import ObjectId

from httpx import AsyncClient, ASGITransport

# Ensure imports work when running pytest from the service folder
SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

# Ensure required env vars for token creation
os.environ.setdefault("SECRET_KEY", "testsecret")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

# import app
import auth_app.main as main_module
from auth_app.main import app

# import hash_password to prepare test flows
from auth_app.security import hash_password


class InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeCollection:
    def __init__(self):
        self._data = {}

    async def insert_one(self, doc):
        _id = doc.get("_id") or str(ObjectId())
        if isinstance(_id, ObjectId):
            pass
        stored = dict(doc)
        stored["_id"] = _id
        self._data[_id] = stored
        return InsertResult(_id)

    async def find_one(self, query):
        # support queries by _id or email
        if "_id" in query:
            _id = query.get("_id")
            if isinstance(_id, ObjectId):
                _id = str(_id)
            return dict(self._data.get(_id)) if _id in self._data else None

        if "email" in query:
            email = query.get("email")
            for doc in self._data.values():
                if doc.get("email") == email:
                    return dict(doc)
        return None


class FakeDB:
    def __init__(self):
        self.users = FakeCollection()

    def __getitem__(self, name):
        if name == "users":
            return self.users
        raise KeyError(name)


class DummyAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, *args, **kwargs):
        class R:
            status_code = 200

        return R()


@pytest.fixture(autouse=True)
def set_fake_db(monkeypatch):
    fake_db = FakeDB()
    # Prevent real DB init during app startup
    try:
        main_module.init_db = lambda a: None
        main_module.close_db = lambda a: None
    except Exception:
        pass

    # Patch the external user-service call inside register handler to avoid network
    post_module = importlib.import_module("auth_app.routes.auth.post")
    try:
        post_module.httpx.AsyncClient = DummyAsyncClient
    except Exception:
        pass

    app.mongodb = fake_db
    yield


@pytest_asyncio.fixture()
async def ac():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_register_and_login(ac):
    payload = {"name": "Test User", "email": "test@example.com", "password": "secret"}
    # register
    r = await ac.post("/auth/register", json=payload)
    assert r.status_code in (200, 201)
    created = r.json()
    assert created.get("email") == payload["email"]

    # login
    login_payload = {"email": payload["email"], "password": payload["password"]}
    r = await ac.post("/auth/login", json=login_payload)
    assert r.status_code == 200
    token = r.json()
    assert "access_token" in token


@pytest.mark.asyncio
async def test_login_invalid_credentials(ac):
    # prepare a user directly in fake DB with hashed password
    user_id = str(ObjectId())
    hashed = hash_password("mypassword")
    app.mongodb.users._data[user_id] = {
        "_id": user_id,
        "name": "U",
        "email": "u@example.com",
        "password": hashed,
        "role": "user",
    }

    r = await ac.post(
        "/auth/login", json={"email": "u@example.com", "password": "wrong"}
    )
    assert r.status_code == 401
