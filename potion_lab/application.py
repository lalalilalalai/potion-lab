"""HTTP и фабрика приложения; источник API — исходный openapi.yaml."""

import logging
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path

import yaml
from fastapi import FastAPI, Request

from generated.dto import HealthResponse
from potion_lab.settings import Settings, load_settings

logger = logging.getLogger("potion_lab")
CONTRACT_PATH = Path(__file__).resolve().parents[1] / "openapi.yaml"


def create_app(settings: Settings | None = None) -> FastAPI:
    selected = load_settings() if settings is None else settings
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    version = contract["info"]["version"]

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "Приложение инициализировано APP_NAME=%r APP_VERSION=%s "
            "host=127.0.0.1 port=%d LOG_LEVEL=%s",
            selected.app_name,
            app.version,
            selected.app_port,
            selected.log_level,
        )
        try:
            yield
        finally:
            logger.info("Приложение остановлено APP_VERSION=%s", app.version)

    app = FastAPI(
        title=selected.app_name,
        version=version,
        lifespan=lifespan,
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
    )
    app.state.settings = selected

    def source_openapi() -> dict:
        return deepcopy(contract)

    app.openapi = source_openapi

    @app.middleware("http")
    async def log_request(request: Request, call_next):
        try:
            response = await call_next(request)
        except Exception:
            route = getattr(request.scope.get("route"), "path", "<неизвестный>")
            logger.error(
                "Ошибка операции method=%s route=%s status=500",
                request.method,
                route,
            )
            raise
        route = getattr(request.scope.get("route"), "path", "<неизвестный>")
        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING
        else:
            level = logging.INFO
        logger.log(
            level,
            "Запрос завершён method=%s route=%s status=%d",
            request.method,
            route,
            response.status_code,
        )
        return response

    @app.get("/health", response_model=HealthResponse, operation_id="get_health")
    async def get_health() -> HealthResponse:
        return HealthResponse(status="ok")

    return app
