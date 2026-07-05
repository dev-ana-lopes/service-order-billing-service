import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .infrastructure.config.settings import Settings, get_settings
from .infrastructure.logging import configure_logging
from .infrastructure.messaging.in_memory_event_publisher import InMemoryEventPublisher
from .infrastructure.observability.metrics import REQUEST_COUNTER, REQUEST_DURATION
from .infrastructure.payment.fake_payment_gateway import FakePaymentGateway
from .infrastructure.repositories.in_memory_billing_repositories import (
    InMemoryPaymentRepository,
    InMemoryQuoteRepository,
)
from .presentation.api.routes import (
    billing_router,
    event_router,
    health_router,
    metrics_router,
)

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="Service Order Billing Service",
        description=(
            "Billing service skeleton for FIAP Phase 4. Endpoints will be added "
            "in later slices."
        ),
        version=settings.APP_VERSION,
    )
    app.state.settings = settings
    app.state.quote_repository = InMemoryQuoteRepository()
    app.state.payment_repository = InMemoryPaymentRepository()
    app.state.event_publisher = InMemoryEventPublisher()
    app.state.payment_gateway = FakePaymentGateway()

    if settings.TRUSTED_HOSTS and settings.TRUSTED_HOSTS != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_operational_headers_and_logs(request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
        request_id = request.headers.get("X-Request-ID", correlation_id)
        started_at = perf_counter()
        response = await call_next(request)
        duration_ms = round((perf_counter() - started_at) * 1000, 2)

        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        route_path = request.url.path
        REQUEST_COUNTER.labels(
            method=request.method, path=route_path, status_code=response.status_code
        ).inc()
        REQUEST_DURATION.labels(method=request.method, path=route_path).observe(
            duration_ms
        )

        logger.info(
            "Request completed",
            extra={
                "correlation_id": correlation_id,
                "request_id": request_id,
                "service": settings.APP_NAME,
                "env": settings.ENVIRONMENT,
                "version": settings.APP_VERSION,
            },
        )
        return response

    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(billing_router)
    app.include_router(event_router)
    return app


app = create_app()
