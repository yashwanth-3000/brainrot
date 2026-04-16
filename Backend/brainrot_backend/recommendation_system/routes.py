from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request

from brainrot_backend.auth import AuthConfigurationError, AuthenticationError
from brainrot_backend.core.models.api import (
    ChatCreateRequest,
    ChatEnvelope,
    ChatGeneratedAssetsResponse,
    ChatListResponse,
    ChatRecommendationResponse,
    ShortEngagementEnvelope,
    ShortEngagementRequest,
)

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("", response_model=ChatEnvelope)
async def create_chat(
    request: Request,
    payload: ChatCreateRequest | None = None,
    authorization: str | None = Header(default=None),
) -> ChatEnvelope:
    container = request.app.state.container
    resolved = payload or ChatCreateRequest()
    auth = await _resolve_auth_context(request, authorization=authorization)
    return await container.chat_service.create_chat(
        auth=auth,
        title=resolved.title,
        source_label=resolved.source_label,
        source_url=resolved.source_url,
    )


@router.get("", response_model=ChatListResponse)
async def list_chats(
    request: Request,
    authorization: str | None = Header(default=None),
) -> ChatListResponse:
    container = request.app.state.container
    auth = await _resolve_auth_context(request, authorization=authorization)
    return await container.chat_service.list_chats(auth)


@router.get("/{chat_id}", response_model=ChatEnvelope)
async def get_chat(
    request: Request,
    chat_id: UUID,
    authorization: str | None = Header(default=None),
) -> ChatEnvelope:
    chat_id: str = str(chat_id)
    container = request.app.state.container
    auth = await _resolve_auth_context(request, authorization=authorization)
    try:
        return await container.chat_service.get_chat(chat_id, auth)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Chat not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/{chat_id}/shorts", response_model=ChatGeneratedAssetsResponse)
async def get_chat_generated_assets(
    request: Request,
    chat_id: UUID,
    authorization: str | None = Header(default=None),
) -> ChatGeneratedAssetsResponse:
    chat_id: str = str(chat_id)
    container = request.app.state.container
    auth = await _resolve_auth_context(request, authorization=authorization)
    try:
        return await container.chat_service.list_chat_generated_assets(chat_id, auth)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Chat not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/{chat_id}/engagement", response_model=ShortEngagementEnvelope)
async def record_chat_short_engagement(
    request: Request,
    chat_id: UUID,
    payload: ShortEngagementRequest,
    authorization: str | None = Header(default=None),
) -> ShortEngagementEnvelope:
    chat_id: str = str(chat_id)
    container = request.app.state.container
    auth = await _resolve_auth_context(request, authorization=authorization)
    try:
        return await container.chat_service.record_short_engagement(chat_id, payload, auth)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Chat or short not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/{chat_id}/recommendations", response_model=ChatRecommendationResponse)
async def get_chat_recommendations(
    request: Request,
    chat_id: UUID,
    session_id: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
) -> ChatRecommendationResponse:
    chat_id: str = str(chat_id)
    container = request.app.state.container
    auth = await _resolve_auth_context(request, authorization=authorization)
    try:
        return await container.chat_service.get_chat_recommendation(chat_id, auth=auth, session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Chat not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


async def _resolve_auth_context(request: Request, authorization: str | None):
    container = request.app.state.container
    try:
        return await container.auth_service.resolve_request(authorization)
    except AuthConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
