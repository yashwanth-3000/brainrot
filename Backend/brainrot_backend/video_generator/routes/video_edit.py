from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

from brainrot_backend.core.models.api import (
    SubtitlePresetOption,
    VideoEditOptionsResponse,
    VideoEditPreviewRequest,
    VideoEditPreviewResponse,
)
from brainrot_backend.core.models.enums import AssetKind
from brainrot_backend.video_generator.render.subtitles import subtitle_presets
from brainrot_backend.video_generator.services.assets import filter_allowed_gameplay_assets

router = APIRouter(prefix="/video-edit", tags=["video-edit"])


def _local_preview_dir(settings, batch_id: str) -> Path:
    return settings.data_dir / settings.final_render_bucket / batch_id


@router.get("/options", response_model=VideoEditOptionsResponse)
async def get_video_edit_options(request: Request) -> VideoEditOptionsResponse:
    container = request.app.state.container
    gameplay_assets = filter_allowed_gameplay_assets(
        container.settings,
        await container.repository.list_assets(AssetKind.GAMEPLAY),
    )
    presets = [
        SubtitlePresetOption(
            id=preset.id,
            label=preset.label,
            animation=preset.animation,
            font_name=preset.font_name,
            preferred_tags=list(preset.preferred_tags),
        )
        for preset in subtitle_presets(container.settings.assets_dir / "fonts")
    ]
    return VideoEditOptionsResponse(gameplay_assets=gameplay_assets, subtitle_presets=presets)


@router.post("/previews", response_model=VideoEditPreviewResponse)
async def create_video_edit_preview(
    request: Request,
    payload: VideoEditPreviewRequest,
) -> VideoEditPreviewResponse:
    container = request.app.state.container
    try:
        envelope = await container.batch_service.create_video_edit_preview(
            title=payload.title,
            narration_text=payload.narration_text,
            gameplay_asset_id=payload.gameplay_asset_id,
            subtitle_preset_id=payload.subtitle_preset_id,
            premium_audio=payload.premium_audio,
            music_asset_id=payload.music_asset_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return VideoEditPreviewResponse(batch=envelope.batch, item=envelope.items[0])


@router.get("/previews/{batch_id}/video")
async def get_video_edit_preview_video(request: Request, batch_id: str):
    container = request.app.state.container
    try:
        envelope = await container.batch_service.get_batch(batch_id)
    except KeyError:
        envelope = None

    if envelope is not None:
        if not envelope.items:
            raise HTTPException(status_code=404, detail="Preview item not found.")

        item = envelope.items[0]
        if not item.output_url:
            preview_dir = _local_preview_dir(container.settings, batch_id)
            fallback_candidates = sorted(preview_dir.glob("*.mp4"))
            if fallback_candidates:
                fallback_path = fallback_candidates[0]
                return FileResponse(fallback_path, media_type="video/mp4", filename=fallback_path.name)
            raise HTTPException(status_code=404, detail="Preview video is not ready yet.")

        if item.output_url.startswith("file://"):
            local_path = Path(urlparse(item.output_url).path)
            if not local_path.exists():
                raise HTTPException(status_code=404, detail="Preview file is missing.")
            return FileResponse(local_path, media_type="video/mp4", filename=local_path.name)

        return RedirectResponse(item.output_url)

    preview_dir = _local_preview_dir(container.settings, batch_id)
    fallback_candidates = sorted(preview_dir.glob("*.mp4"))
    if fallback_candidates:
        fallback_path = fallback_candidates[0]
        return FileResponse(fallback_path, media_type="video/mp4", filename=fallback_path.name)

    raise HTTPException(status_code=404, detail="Preview batch not found.")
