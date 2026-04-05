from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from brainrot_backend.shared.models.api import (
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
async def create_chat(request: Request, payload: ChatCreateRequest | None = None) -> ChatEnvelope:
    container = request.app.state.container
    resolved = payload or ChatCreateRequest()
    return await container.chat_service.create_chat(
        title=resolved.title,
        source_label=resolved.source_label,
        source_url=resolved.source_url,
    )


@router.get("", response_model=ChatListResponse)
async def list_chats(request: Request) -> ChatListResponse:
    container = request.app.state.container
    return await container.chat_service.list_chats()


@router.get("/{chat_id}", response_model=ChatEnvelope)
async def get_chat(request: Request, chat_id: str) -> ChatEnvelope:
    container = request.app.state.container
    try:
        return await container.chat_service.get_chat(chat_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Chat not found.") from exc


@router.get("/{chat_id}/shorts", response_model=ChatGeneratedAssetsResponse)
async def get_chat_generated_assets(request: Request, chat_id: str) -> ChatGeneratedAssetsResponse:
    container = request.app.state.container
    return await container.chat_service.list_chat_generated_assets(chat_id)


@router.post("/{chat_id}/engagement", response_model=ShortEngagementEnvelope)
async def record_chat_short_engagement(
    request: Request,
    chat_id: str,
    payload: ShortEngagementRequest,
) -> ShortEngagementEnvelope:
    container = request.app.state.container
    try:
        return await container.chat_service.record_short_engagement(chat_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Chat or short not found.") from exc


@router.get("/{chat_id}/recommendations", response_model=ChatRecommendationResponse)
async def get_chat_recommendations(
    request: Request,
    chat_id: str,
    session_id: str | None = Query(default=None),
) -> ChatRecommendationResponse:
    container = request.app.state.container
    try:
        return await container.chat_service.get_chat_recommendation(chat_id, session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Chat not found.") from exc
