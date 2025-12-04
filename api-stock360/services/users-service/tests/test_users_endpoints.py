import os
import sys
from pathlib import Path
import pytest
import pytest_asyncio
from bson import ObjectId

from httpx import AsyncClient, ASGITransport

# Ensure imports work when running pytest from the service folder
SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

# Set env var for API key used by auth helper
os.environ.setdefault("USERS_API_KEY", "testkey")

# import app
import users_app.main as main_module
from users_app.main import app


class InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class UpdateResult:
    def __init__(self, matched_count=0, modified_count=0):
        self.matched_count = matched_count
        self.modified_count = modified_count


class FakeCollection:
    def __init__(self):
        self._data = {}

    async def insert_one(self, doc):
        _id = doc.get("_id") or ObjectId()
        if isinstance(_id, str):
            try:
                _id = ObjectId(_id)
            except Exception:
                pass
        stored = dict(doc)
        stored["_id"] = _id
        self._data[_id] = stored
        return InsertResult(_id)

    async def find_one(self, query, projection=None):
        _id = query.get("_id")
        if _id is None:
            return None
        if isinstance(_id, str):
            try:
                _id = ObjectId(_id)
            except Exception:
                return None
        doc = self._data.get(_id)
        if doc is None:
            return None
        out = dict(doc)
        # compatibility: some handlers expect 'username' field in response models
        if "name" in out and "username" not in out:
            out["username"] = out["name"]
        return out

    def _match_filter(self, doc, query):
        for k, v in query.items():
            if doc.get(k) != v:
                return False
        return True

    def find(self, query=None):
        query = query or {}

        class AsyncCursor:
            def __init__(self, items):
                self._items = items

            def sort(self, *_args, **_kwargs):
                return self

            def __aiter__(self):
                self._iter = iter(self._items)
                return self

            async def __anext__(self):
                try:
                    return next(self._iter)
                except StopIteration:
                    raise StopAsyncIteration

        items = []
        for doc in self._data.values():
            if self._match_filter(doc, query):
                items.append(dict(doc))
        return AsyncCursor(items)

    async def update_one(self, query, update):
        _id = query.get("_id")
        if isinstance(_id, str):
            try:
                _id = ObjectId(_id)
            except Exception:
                return UpdateResult(0, 0)
        doc = self._data.get(_id)
        if not doc:
            return UpdateResult(0, 0)
        set_data = update.get("$set", {})
        doc.update(set_data)
        self._data[_id] = doc
        return UpdateResult(1, 1)


class FakeDB:
    def __init__(self):
        self.users = FakeCollection()

    def __getitem__(self, name):
        if name == "users":
            return self.users
        raise KeyError(name)


@pytest.fixture(autouse=True)
def set_fake_db(monkeypatch):
    fake_db = FakeDB()
    app.mongodb = fake_db
    yield


@pytest_asyncio.fixture()
async def ac():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


async def create_sample_user(client, headers=None):
    headers = headers or {"X-API-Key": "testkey"}
    user_id = str(ObjectId())
    payload = {
        "id": user_id,
        "name": "Alice",
        "email": "alice@example.com",
        "role": "user",
    }
    r = await client.post("/users/", json=payload, headers=headers)
    assert r.status_code in (200, 201)
    created = r.json() or {}
    created_id = created.get("id") or created.get("_id") or user_id
    return created_id


@pytest.mark.asyncio
async def test_create_user(ac):
    headers = {"X-API-Key": "testkey"}
    payload = {
        "id": str(ObjectId()),
        "name": "Bob",
        "email": "bob@example.com",
        "role": "user",
    }
    r = await ac.post("/users/", json=payload, headers=headers)
    assert r.status_code in (200, 201)
    created = r.json()
    assert (
        created.get("name") == payload["name"]
        or created.get("username") == payload["name"]
    )


@pytest.mark.asyncio
async def test_get_user(ac):
    headers = {"X-API-Key": "testkey"}
    created_id = await create_sample_user(ac, headers)

    r = await ac.get(f"/users/{created_id}", headers=headers)
    assert r.status_code == 200
    single = r.json()
    assert single.get("id") == created_id or single.get("id") == str(
        ObjectId(created_id)
    )


@pytest.mark.asyncio
async def test_update_user(ac):
    headers = {"X-API-Key": "testkey"}
    created_id = await create_sample_user(ac, headers)

    update_payload = {"name": "Updated Name"}
    r = await ac.put(f"/users/{created_id}", json=update_payload, headers=headers)
    assert r.status_code == 200
    # verify stored value
    stored = await app.mongodb.users.find_one({"_id": ObjectId(created_id)})
    assert stored is not None
    assert stored.get("name") == "Updated Name"
