"""HTTP и фабрика приложения; источник API — исходный openapi.yaml."""

import logging
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path
from typing import Annotated

import yaml
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import Field

from generated.dto import (
    BrewRequest,
    BusinessError,
    Code,
    Detail,
    HealthResponse,
    HTTPValidationError,
    Ingredient,
    Potion,
    Reaction,
    ReactRequest,
    VersionResponse,
)
from potion_lab import domain
from potion_lab.settings import Settings, load_settings

logger = logging.getLogger("potion_lab")
CONTRACT_PATH = Path(__file__).resolve().parents[1] / "openapi.yaml"


def _log_route(request: Request) -> str:
    route = getattr(request.scope.get("route"), "path", None)
    if route is not None:
        return route
    path = request.scope.get("path")
    return path if path in ("/docs", "/openapi.json") else "<неизвестный>"


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

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        request.state.error_code = "validation_error"
        details = [
            {"loc": list(issue["loc"]), "msg": issue["msg"], "type": issue["type"]}
            for issue in error.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": details})

    @app.middleware("http")
    async def log_request(request: Request, call_next):
        try:
            response = await call_next(request)
        except Exception:
            route = _log_route(request)
            logger.error(
                "Ошибка операции method=%s route=%s status=500",
                request.method,
                route,
            )
            raise
        route = _log_route(request)
        if response.status_code >= 500:
            level = logging.ERROR
        elif (
            response.status_code >= 400
            or getattr(request.state, "outcome", None) == "explosion"
        ):
            level = logging.WARNING
        else:
            level = logging.INFO
        logger.log(
            level,
            "Запрос завершён method=%s route=%s status=%d code=%s outcome=%s",
            request.method,
            route,
            response.status_code,
            getattr(
                request.state,
                "error_code",
                "http_error" if response.status_code >= 400 else "ok",
            ),
            getattr(request.state, "outcome", "-"),
        )
        return response

    @app.get("/health", response_model=HealthResponse, operation_id="get_health")
    async def get_health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/version", response_model=VersionResponse, operation_id="get_version")
    async def get_version() -> VersionResponse:
        return VersionResponse(version=version)

    @app.get(
        "/ingredients",
        response_model=Annotated[list[Ingredient], Field(min_length=5, max_length=5)],
        operation_id="list_ingredients",
        tags=["Ingredients"],
    )
    async def get_ingredients() -> list[Ingredient]:
        return domain.list_ingredients()

    @app.post(
        "/potions/brew",
        response_model=Potion,
        operation_id="brew_potion",
        tags=["Potions"],
        responses={
            400: {"model": BusinessError},
            422: {"model": HTTPValidationError},
        },
    )
    async def brew_potion(
        recipe: BrewRequest, request: Request
    ) -> Potion | JSONResponse:
        try:
            return domain.brew_potion(recipe)
        except domain.DuplicateIngredientError:
            request.state.error_code = "duplicate_ingredient"
            error = BusinessError(
                detail=Detail(
                    code=Code.duplicate_ingredient,
                    message="Каждый ингредиент можно указать только один раз.",
                )
            )
            return JSONResponse(status_code=400, content=error.model_dump(mode="json"))

    @app.post(
        "/potions/react",
        response_model=Reaction,
        operation_id="react_potions",
        tags=["Potions"],
        responses={422: {"model": HTTPValidationError}},
    )
    async def react_potions(experiment: ReactRequest, request: Request) -> Reaction:
        result = domain.react_potions(experiment)
        request.state.outcome = getattr(
            result.root.outcome, "value", result.root.outcome
        )
        return result

    return app
