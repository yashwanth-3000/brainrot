from __future__ import annotations

import json

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from brainrot_backend.shared.models.api import AssetUploadResponse
from brainrot_backend.shared.models.enums import AssetKind

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("/upload", response_model=AssetUploadResponse)
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    kind: AssetKind = Form(...),
    tags: str = Form(""),
    metadata_json: str = Form("{}"),
) -> AssetUploadResponse:
    container = request.app.state.container
    try:
        metadata = json.loads(metadata_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid metadata_json: {exc}") from exc

    payload = await file.read()
    asset = await container.asset_service.upload_asset(
        kind=kind,
        filename=file.filename or "upload.bin",
        content=payload,
        tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
        metadata=metadata,
        content_type=file.content_type,
    )
    return AssetUploadResponse(asset=asset)
