from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from brainrot_backend.models.api import ChatCreateRequest, ChatEnvelope, ChatGeneratedAssetsResponse, ChatListResponse

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
