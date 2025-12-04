import os
import sys
from pathlib import Path
import pytest
import pytest_asyncio
from datetime import datetime
from bson import ObjectId

from httpx import AsyncClient, ASGITransport

# Ensure imports work when running pytest from the service folder
SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

# Set env vars for auth helpers (if any)
os.environ.setdefault("TOOLS_API_KEY", "testkey")

# import app
import tools_app.main as main_module
from tools_app.main import app


class InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class UpdateResult:
    def __init__(self, matched_count=0, modified_count=0):
        self.matched_count = matched_count
        self.modified_count = modified_count


class DeleteResult:
    def __init__(self, deleted_count=0):
        self.deleted_count = deleted_count


class FakeCollection:
    def __init__(self):
        self._data = {}

    async def insert_one(self, doc):
        _id = doc.get("_id") or ObjectId()
        if isinstance(_id, str):
            _id = ObjectId(_id)
        stored = dict(doc)
        stored["_id"] = _id
        self._data[_id] = stored
        return InsertResult(_id)

    async def find_one(self, query):
        _id = query.get("_id")
        if _id is None:
            return None
        if isinstance(_id, str):
            try:
                _id = ObjectId(_id)
            except Exception:
                return None
        doc = self._data.get(_id)
        return dict(doc) if doc is not None else None

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

    async def delete_one(self, query):
        _id = query.get("_id")
        if isinstance(_id, str):
            try:
                _id = ObjectId(_id)
            except Exception:
                return DeleteResult(0)
        if _id in self._data:
            del self._data[_id]
            return DeleteResult(1)
        return DeleteResult(0)


class FakeDB:
    def __init__(self):
        self.inventory = FakeCollection()

    def __getitem__(self, name):
        if name == "inventory":
            return self.inventory
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


async def create_sample_item(client, headers=None):
    headers = headers or {"X-API-Key": "testkey"}
    payload = {
        "name": "Cement Bag",
        "description": "Type II",
        "unit": "bags",
        "quantity_on_hand": 100,
        "min_quantity": 10,
        "is_active": True,
    }
    r = await client.post("/tools/", json=payload, headers=headers)
    assert r.status_code in (200, 201)
    created = r.json() or {}
    created_id = created.get("id") or created.get("_id")
    if not created_id:
        keys = list(app.mongodb.inventory._data.keys())
        assert len(keys) == 1
        created_id = str(keys[0])
    return created_id


@pytest.mark.asyncio
async def test_create_item(ac):
    headers = {"X-API-Key": "testkey"}
    payload = {
        "name": "Gravel",
        "unit": "tons",
        "quantity_on_hand": 50,
        "min_quantity": 5,
    }
    r = await ac.post("/tools/", json=payload, headers=headers)
    assert r.status_code in (200, 201)
    created = r.json()
    assert created.get("name") == "Gravel" or created.get("name") == payload["name"]


@pytest.mark.asyncio
async def test_list_and_get_item(ac):
    headers = {"X-API-Key": "testkey"}
    created_id = await create_sample_item(ac, headers)

    r = await ac.get("/tools/", headers=headers)
    assert r.status_code == 200
    items = r.json()
    assert any(
        it.get("id") == str(ObjectId(created_id)) or it.get("id") == created_id
        for it in items
    )

    r = await ac.get(f"/tools/{created_id}", headers=headers)
    assert r.status_code == 200
    single = r.json()
    assert (
        single.get("id") == str(ObjectId(created_id)) or single.get("id") == created_id
    )


@pytest.mark.asyncio
async def test_update_item(ac):
    headers = {"X-API-Key": "testkey"}
    created_id = await create_sample_item(ac, headers)

    update_payload = {"quantity_on_hand": 80}
    r = await ac.put(f"/tools/{created_id}", json=update_payload, headers=headers)
    assert r.status_code == 200
    # verify stored value
    stored = await app.mongodb.inventory.find_one({"_id": ObjectId(created_id)})
    assert stored is not None
    assert stored.get("quantity_on_hand") == 80


@pytest.mark.asyncio
async def test_delete_item(ac):
    headers = {"X-API-Key": "testkey"}
    created_id = await create_sample_item(ac, headers)

    r = await ac.delete(f"/tools/{created_id}", headers=headers)
    assert r.status_code in (200, 204)

    r = await ac.get(f"/tools/{created_id}", headers=headers)
    assert r.status_code == 404
