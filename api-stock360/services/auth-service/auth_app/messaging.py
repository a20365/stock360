import json
import os
import logging

import aio_pika
from aio_pika import ExchangeType

logger = logging.getLogger(__name__)


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
EXCHANGE_NAME = os.getenv("USER_EVENTS_EXCHANGE", "user.events")
ROUTING_KEY_USER_CREATED = os.getenv("USER_CREATED_ROUTING_KEY", "user.created")


async def publish_user_created_event(payload: dict) -> None:
    """Publish a user.created event to RabbitMQ (fire-and-forget)."""
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
        )
        message = aio_pika.Message(
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key=ROUTING_KEY_USER_CREATED)
        await connection.close()
    except Exception as exc:  # pragma: no cover - log and continue
        logger.error("Failed to publish user.created event: %s", exc)
        # We deliberately do not raise to avoid failing the user registration path
