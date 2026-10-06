import uvicorn
from fastapi import FastAPI
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncEngine

from async_payments_service.api.errors import register_exception_handlers
from async_payments_service.api.lifespan import ShutdownHook, StartupHook, lifespan
from async_payments_service.api.middleware import CorrelationIdMiddleware
from async_payments_service.api.routes.health import router as health_router
from async_payments_service.api.routes.payments import router as payments_router
from async_payments_service.core.config import get_settings
from async_payments_service.core.logging import configure_logging
from async_payments_service.core.metadata import service_title, service_version
from async_payments_service.core.readiness import ReadinessCheck
from async_payments_service.db.engine import create_engine, ping_database
from async_payments_service.db.session import create_session_factory
from async_payments_service.messaging.broker import create_broker, ping_broker


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(
        title=service_title(),
        version=service_version(),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    application.state.startup_hooks = [_start_database(application), _start_broker(application)]
    application.state.shutdown_hooks = [_stop_database(application), _stop_broker(application)]
    application.state.readiness_checks = {}
    application.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(payments_router)
    return application


def _database_check(engine: AsyncEngine) -> ReadinessCheck:
    async def check() -> None:
        await ping_database(engine)

    return check


def _broker_check(broker: RabbitBroker) -> ReadinessCheck:
    async def check() -> None:
        await ping_broker(broker)

    return check


def _start_database(app: FastAPI) -> StartupHook:
    async def start() -> None:
        engine = create_engine(get_settings())
        app.state.db_engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.readiness_checks["db"] = _database_check(engine)

    return start


def _stop_database(app: FastAPI) -> ShutdownHook:
    async def stop() -> None:
        app.state.readiness_checks.pop("db", None)
        engine: AsyncEngine | None = getattr(app.state, "db_engine", None)
        if engine is not None:
            await engine.dispose()

    return stop


def _start_broker(app: FastAPI) -> StartupHook:
    async def start() -> None:
        broker = create_broker(get_settings())
        await broker.connect()
        app.state.broker = broker
        app.state.readiness_checks["broker"] = _broker_check(broker)

    return start


def _stop_broker(app: FastAPI) -> ShutdownHook:
    async def stop() -> None:
        app.state.readiness_checks.pop("broker", None)
        broker: RabbitBroker | None = getattr(app.state, "broker", None)
        if broker is not None:
            await broker.stop()

    return stop


app = create_app()


def main() -> None:
    settings = get_settings()
    uvicorn.run(app, host=settings.api_host, port=settings.api_port, log_config=None)
