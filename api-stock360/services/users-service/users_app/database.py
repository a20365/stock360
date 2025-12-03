import os

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.getenv("DATABASE_URL")


def init_db(app: FastAPI):
    if not MONGO_URL:
        raise ValueError("DATABASE_URL not set")

    client = AsyncIOMotorClient(MONGO_URL)
    app.mongodb_client = client
    db_name = os.getenv("USERS_DB")
    if not db_name:
        raise ValueError("USERS_DB not set")
    app.mongodb = client[db_name]


def close_db(app: FastAPI):
    app.mongodb_client.close()
