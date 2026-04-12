from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sse_starlette.sse import EventSourceResponse

from brainrot_backend.shared.models.api import BatchEnvelope, BatchRetryResponse
from brainrot_backend.shared.models.enums import SourceKind

router = APIRouter(prefix="/batches", tags=["batches"])


def _local_render_path(settings, batch_id: str, item_id: str) -> Path:
    return settings.data_dir / settings.final_render_bucket / batch_id / f"{item_id}.mp4"


def _video_response_from_output_url(output_url: str):
    if output_url.startswith("file://"):
        local_path = Path(urlparse(output_url).path)
        if not local_path.exists():
            raise HTTPException(status_code=404, detail="Video file is missing.")
        return FileResponse(local_path, media_type="video/mp4", filename=local_path.name)
    return RedirectResponse(output_url)


@router.post("", response_model=BatchEnvelope)
async def create_batch(
    request: Request,
    source_url: str | None = Form(None),
    source_kind: SourceKind | None = Form(None),
    count: int = Form(...),
    chat_id: str | None = Form(None),
    title_hint: str | None = Form(None),
    producer_agent_config_id: str | None = Form(None),
    narrator_agent_config_id: str | None = Form(None),
    premium_audio: bool = Form(False),
    file: UploadFile | None = File(None),
) -> BatchEnvelope:
    if count < 5 or count > 15:
        raise HTTPException(status_code=422, detail="count must be between 5 and 15.")
    if not source_url and file is None:
        raise HTTPException(status_code=422, detail="Either source_url or file must be provided.")

    inferred_kind = source_kind or infer_source_kind(source_url, file)
    payload = await file.read() if file is not None else None

    container = request.app.state.container
    try:
        return await container.batch_service.create_batch(
            source_kind=inferred_kind,
            source_url=source_url,
            count=count,
            chat_id=chat_id,
            title_hint=title_hint,
            producer_agent_config_id=producer_agent_config_id,
            narrator_agent_config_id=narrator_agent_config_id,
            premium_audio=premium_audio,
            uploaded_filename=file.filename if file else None,
            uploaded_bytes=payload,
            uploaded_content_type=file.content_type if file else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{batch_id}", response_model=BatchEnvelope)
async def get_batch(request: Request, batch_id: str) -> BatchEnvelope:
    container = request.app.state.container
    try:
        return await container.batch_service.get_batch(batch_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Batch not found.") from exc


@router.get("/{batch_id}/items/{item_id}/video")
async def get_batch_item_video(request: Request, batch_id: str, item_id: str):
    container = request.app.state.container
    try:
        envelope = await container.batch_service.get_batch(batch_id)
    except KeyError:
        envelope = None

    if envelope is not None:
        item = next((candidate for candidate in envelope.items if candidate.id == item_id), None)
        if item is not None and item.output_url:
            return _video_response_from_output_url(item.output_url)
        if item is not None:
            fallback_path = _local_render_path(container.settings, batch_id, item_id)
            if fallback_path.exists():
                return FileResponse(fallback_path, media_type="video/mp4", filename=fallback_path.name)
            raise HTTPException(status_code=404, detail="Video is not ready yet.")

    fallback_path = _local_render_path(container.settings, batch_id, item_id)
    if fallback_path.exists():
        return FileResponse(fallback_path, media_type="video/mp4", filename=fallback_path.name)

    raise HTTPException(status_code=404, detail="Batch item video not found.")


@router.get("/{batch_id}/events")
async def stream_events(request: Request, batch_id: str, last_event_id: str | None = None):
    container = request.app.state.container
    after_sequence = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0
    generator = container.events.stream(batch_id, after_sequence=after_sequence)
    return EventSourceResponse(generator)


@router.post("/{batch_id}/retry", response_model=BatchRetryResponse)
async def retry_failed_items(request: Request, batch_id: str) -> BatchRetryResponse:
    container = request.app.state.container
    try:
        retried = await container.batch_service.retry_failed_items(batch_id)
        envelope = await container.batch_service.get_batch(batch_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Batch not found.") from exc
    return BatchRetryResponse(batch=envelope.batch, retried_item_ids=retried)


def infer_source_kind(source_url: str | None, file: UploadFile | None) -> SourceKind:
    if file is not None:
        return SourceKind.PDF_UPLOAD
    assert source_url is not None
    parsed = urlparse(source_url)
    path = parsed.path.lower()
    if path.endswith(".pdf"):
        return SourceKind.PDF_URL
    if path in {"", "/"}:
        return SourceKind.WEBSITE
    return SourceKind.ARTICLE
