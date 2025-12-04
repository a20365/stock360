import time
import asyncio

from fastapi import FastAPI
from prometheus_client import Counter, Histogram, make_asgi_app
from starlette.requests import Request

from .database import close_db, init_db
from .routes.users import router as users_router
from .messaging import start_consumer_background

app = FastAPI(title="Users Service")

USERS_SERVICE_NAME = "users-service"

REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP Requests",
    ["method", "endpoint", "status_code", "service"],
)

REQUEST_ERRORS_TOTAL = Counter(
    "http_error_requests_total",
    "Total HTTP Error Requests",
    ["method", "endpoint", "status_code", "service"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP Request Latency",
    ["method", "endpoint", "service"],
    buckets=[0.05, 0.1, 0.3, 0.5, 1, 2, 5],
)


@app.middleware("http")
async def add_prometheus_metrics(request: Request, call_next):
    start_time = time.time()
    endpoint = request.url.path
    method = request.method

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        REQUEST_ERRORS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            service=USERS_SERVICE_NAME,
        ).inc()
        raise e
    else:
        if 400 <= status_code < 600:
            REQUEST_ERRORS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                service=USERS_SERVICE_NAME,
            ).inc()

    REQUESTS_TOTAL.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code,
        service=USERS_SERVICE_NAME,
    ).inc()

    latency = time.time() - start_time
    REQUEST_LATENCY.labels(
        method=method, endpoint=endpoint, service=USERS_SERVICE_NAME
    ).observe(latency)

    return response


metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.on_event("startup")
async def startup_event():
    init_db(app)
    app.state.user_created_consumer = start_consumer_background(app)


@app.on_event("shutdown")
async def shutdown_event():
    close_db(app)
    consumer = getattr(app.state, "user_created_consumer", None)
    if consumer:
        consumer.cancel()
        try:
            await consumer
        except asyncio.CancelledError:
            pass


@app.get("/")
def health():
    return {"status": "ok", "service": USERS_SERVICE_NAME}


app.include_router(users_router, prefix="/users")
