from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from brainrot_backend.video_generator.routes.agents import router as agents_router
from brainrot_backend.video_generator.routes.assets import router as assets_router
from brainrot_backend.video_generator.routes.batches import router as batches_router
from brainrot_backend.recommendation_system.routes import router as chats_router
from brainrot_backend.video_generator.routes.video_edit import router as video_edit_router
from brainrot_backend.config import Settings
from brainrot_backend.core.models.api import HealthResponse
from brainrot_backend.container import build_container

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()

    logging.basicConfig(
        level=getattr(logging, resolved_settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container = build_container(resolved_settings)
        app.state.container = container
        chat_sync_task: asyncio.Task[None] | None = None
        logger.info(
            "Brainrot Backend started (env=%s, elevenlabs=%s, storage=%s, supabase=%s, firecrawl=%s)",
            resolved_settings.environment,
            resolved_settings.elevenlabs_enabled,
            resolved_settings.resolved_storage_backend,
            resolved_settings.supabase_enabled,
            resolved_settings.firecrawl_enabled,
        )
        if resolved_settings.auto_seed_assets:
            try:
                seeded_gameplay = await container.asset_service.auto_seed_gameplay_assets()
                if seeded_gameplay > 0:
                    logger.info("Auto-seeded %d gameplay assets on startup", seeded_gameplay)
                seeded_fonts = await container.asset_service.auto_seed_font_assets()
                if seeded_fonts > 0:
                    logger.info("Auto-seeded %d subtitle fonts on startup", seeded_fonts)
            except Exception as exc:
                logger.warning("Auto-seed failed (non-fatal): %s", exc)

        async def sync_existing_chats_in_background() -> None:
            try:
                await container.chat_service.sync_existing_chats()
            except Exception as exc:
                logger.warning("Chat summary sync failed (non-fatal): %s", exc)

        chat_sync_task = asyncio.create_task(sync_existing_chats_in_background())
        try:
            yield
        finally:
            if chat_sync_task is not None and not chat_sync_task.done():
                chat_sync_task.cancel()
                with suppress(asyncio.CancelledError):
                    await chat_sync_task

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)
    app.include_router(assets_router, prefix=resolved_settings.api_prefix)
    app.include_router(agents_router, prefix=resolved_settings.api_prefix)
    app.include_router(batches_router, prefix=resolved_settings.api_prefix)
    app.include_router(chats_router, prefix=resolved_settings.api_prefix)
    app.include_router(video_edit_router, prefix=resolved_settings.api_prefix)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    return app


app = create_app()
