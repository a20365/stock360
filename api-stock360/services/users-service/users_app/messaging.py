import asyncio
import json
import logging
import os

import aio_pika
from aio_pika import ExchangeType

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
EXCHANGE_NAME = os.getenv("USER_EVENTS_EXCHANGE", "user.events")
ROUTING_KEY_USER_CREATED = os.getenv("USER_CREATED_ROUTING_KEY", "user.created")
QUEUE_NAME = os.getenv("USER_CREATED_QUEUE", "users-service.user-created")


async def upsert_user_profile(app, payload: dict) -> None:
    users_col = app.mongodb["users"]
    user_id = payload.get("id")
    if not user_id:
        raise ValueError("Missing user id in event")

    doc = {
        "_id": user_id,
        "name": payload.get("name"),
        "email": payload.get("email"),
        "role": payload.get("role", "user"),
    }
    await users_col.update_one({"_id": user_id}, {"$set": doc}, upsert=True)


async def _handle_message(app, message: aio_pika.IncomingMessage):
    async with message.process(requeue=False):
        try:
            payload = json.loads(message.body.decode("utf-8"))
            await upsert_user_profile(app, payload)
        except Exception as exc:
            logger.error("Failed to process user.created message: %s", exc, exc_info=True)


async def consume_user_created(app):
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        exchange = await channel.declare_exchange(EXCHANGE_NAME, ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)
        await queue.bind(exchange, ROUTING_KEY_USER_CREATED)

        logger.info("RabbitMQ consumer started successfully, listening on queue: %s", QUEUE_NAME)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await _handle_message(app, message)

        await connection.close()
    except Exception as exc:
        logger.error("Failed to start RabbitMQ consumer: %s", exc, exc_info=True)
        raise


def start_consumer_background(app):
    return asyncio.create_task(consume_user_created(app))
