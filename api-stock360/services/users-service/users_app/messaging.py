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
MAX_RETRIES = int(os.getenv("USER_CREATED_MAX_RETRIES", "5"))


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

    await users_col.update_one(
        {"_id": user_id},
        {"$set": doc},
        upsert=True,
    )


def get_retry_count(message: aio_pika.IncomingMessage) -> int:
    if not message.headers:
        return 0
    x_death = message.headers.get("x-death")
    if not x_death:
        return 0
    return x_death[0].get("count", 0)


async def _handle_message(app, message: aio_pika.IncomingMessage):
    try:
        payload = json.loads(message.body.decode("utf-8"))
        await upsert_user_profile(app, payload)

        await message.ack()

    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in user.created message: %s", exc, exc_info=True)
        await message.nack(requeue=False)

    except Exception:
        retries = get_retry_count(message)

        if retries >= MAX_RETRIES:
            logger.error(
                "Max retries (%s) reached for message %s. Sending to DLQ.",
                MAX_RETRIES,
                message.message_id,
                exc_info=True,
            )
            await message.nack(requeue=False)
        else:
            logger.warning(
                "Error processing message %s. Retry %s/%s.",
                message.message_id,
                retries + 1,
                MAX_RETRIES,
                exc_info=True,
            )
            await message.nack(requeue=True)


async def consume_user_created(app):
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()

        await channel.set_qos(prefetch_count=10)

        exchange = await channel.declare_exchange(
            EXCHANGE_NAME,
            ExchangeType.TOPIC,
            durable=True,
        )

        dlx = await channel.declare_exchange(
            "user.events.dlx",
            ExchangeType.TOPIC,
            durable=True,
        )

        dlq = await channel.declare_queue(
            f"{QUEUE_NAME}.dlq",
            durable=True,
        )

        await dlq.bind(dlx, ROUTING_KEY_USER_CREATED)

        queue = await channel.declare_queue(
            QUEUE_NAME,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "user.events.dlx",
            },
        )

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
