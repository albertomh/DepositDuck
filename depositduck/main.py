"""
FastAPI application entrypoint.
Defines two apps:
- webapp: main app and entrypoint, serves the htmx frontend
- llmapp: language agent functionality eg. ingest data, generate embeddings, etc.

Usage: point a compatible ASGI server (eg. uvicorn) to `webapp` in this module.

(c) 2024 Alberto Morón Hernández
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from depositduck import (
    APIAPP_ROUTE_TAGS,
    VERSION_MAJOR,
    VERSION_MINOR,
    VERSION_PATCH,
    WEBAPP_ROUTE_TAGS,
)
from depositduck.api.routes import api_router
from depositduck.auth.routes import auth_frontend_router, auth_operations_router
from depositduck.dashboard.routes import (
    dashboard_frontend_router,
    dashboard_operations_router,
)
from depositduck.dependables import get_settings
from depositduck.kitchensink.routes import kitchensink_router
from depositduck.llm.routes import llm_router
from depositduck.settings import Settings

VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
settings = get_settings()
if settings.debug:
    VERSION = f"WIP (on {VERSION})"


def get_apiapp(settings: Settings) -> FastAPI:
    apiapp = FastAPI(
        title=f"⚙️ {settings.app_name} apiapp",
        description="",
        version=VERSION,
        debug=settings.debug,
        openapi_tags=APIAPP_ROUTE_TAGS,
        openapi_url="/openapi.json" if settings.debug else None,
    )
    apiapp.include_router(api_router)
    return apiapp


def get_llmapp(settings: Settings) -> FastAPI:
    llmapp = FastAPI(
        title=f"🤖 {settings.app_name} llmapp",
        description="",
        version=VERSION,
        debug=settings.debug,
        openapi_tags=WEBAPP_ROUTE_TAGS,
        openapi_url="/openapi.json" if settings.debug else None,
    )
    llmapp.include_router(llm_router)
    return llmapp


def get_webapp(settings: Settings) -> FastAPI:
    webapp = FastAPI(
        title=f"🦆 {settings.app_name} webapp",
        description="",
        version=VERSION,
        debug=settings.debug,
        openapi_tags=WEBAPP_ROUTE_TAGS,
        openapi_url="/openapi.json" if settings.debug else None,
        default_response_class=HTMLResponse,
    )
    webapp.include_router(auth_frontend_router)
    webapp.include_router(auth_operations_router)
    webapp.include_router(dashboard_frontend_router)
    webapp.include_router(dashboard_operations_router)
    if settings.debug:
        webapp.include_router(kitchensink_router)

    static_dir_by_package = [("depositduck.web", "static")]
    webapp.mount("/static", StaticFiles(packages=static_dir_by_package), name="static")  # type: ignore[arg-type]

    apiapp = get_apiapp(settings)
    webapp.mount("/api", apiapp)
    llmapp = get_llmapp(settings)
    webapp.mount("/llm", llmapp)

    return webapp


webapp = get_webapp(settings)
