from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.errors import register_error_handlers
from app.routers.data import router as data_router
from app.routers.conversations import router as conversations_router
from app.routers.chat import router as chat_router


def create_app(
    settings: Settings | None = None,
    **service_overrides: Any,
) -> FastAPI:
    active_settings = settings or Settings.from_env()
    app = FastAPI(
        title="Study Coach AI API",
        version="0.1.0",
        description="개인 학습시간 데이터 기반 AI 코치 백엔드",
    )
    app.state.settings = active_settings
    if settings is None and not service_overrides:
        from app.bootstrap import build_services

        services = build_services(active_settings)
        service_overrides = {
            "data_service": services.data_service,
            "summary_service": services.summary_service,
            "conversation_service": services.conversation_service,
            "chat_service": services.chat_service,
        }
    for name, service in service_overrides.items():
        setattr(app.state, name, service)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(data_router)
    app.include_router(conversations_router)
    app.include_router(chat_router)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
