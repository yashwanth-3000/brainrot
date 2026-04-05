from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from brainrot_backend.shared.models.api import AgentBootstrapResponse, WebhookAckResponse
from brainrot_backend.shared.models.domain import ToolScriptBundlePayload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/bootstrap", response_model=AgentBootstrapResponse)
async def bootstrap_agents(request: Request) -> AgentBootstrapResponse:
    container = request.app.state.container
    public_base_url = container.settings.public_base_url or str(request.base_url).rstrip("/")
    try:
        agents, tool_ids = await container.agent_service.bootstrap_agents(public_base_url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AgentBootstrapResponse(agents=agents, tool_ids=tool_ids)


@router.post("/custom-llm")
@router.post("/custom-llm/chat/completions")
@router.post("/custom-llm/chat/completions/chat/completions")
async def custom_llm_chat_completions(
    request: Request,
    authorization: str | None = Header(default=None),
) -> Response:
    container = request.app.state.container
    _validate_bearer(authorization, container.settings.elevenlabs_custom_llm_token, "custom LLM proxy")
    body = await request.body()
    try:
        status_code, content_type, iterator = await container.agent_service.forward_custom_llm_request(
            body=body,
            content_type=request.headers.get("content-type"),
            endpoint_hint="chat_completions",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(iterator, status_code=status_code, media_type=content_type)


@router.post("/custom-llm/responses")
@router.post("/custom-llm/responses/responses")
async def custom_llm_responses(
    request: Request,
    authorization: str | None = Header(default=None),
) -> Response:
    container = request.app.state.container
    _validate_bearer(authorization, container.settings.elevenlabs_custom_llm_token, "custom LLM proxy")
    body = await request.body()
    try:
        status_code, content_type, iterator = await container.agent_service.forward_custom_llm_request(
            body=body,
            content_type=request.headers.get("content-type"),
            endpoint_hint="responses",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(iterator, status_code=status_code, media_type=content_type)


@router.post("/tools/submit-script-bundle", response_model=WebhookAckResponse)
async def submit_script_bundle(
    request: Request,
    authorization: str | None = Header(default=None),
) -> WebhookAckResponse:
    container = request.app.state.container
    _validate_bearer(authorization, container.settings.elevenlabs_tool_token, "submit_script_bundle")
    try:
        raw = await request.json()
        logger.info("submit_script_bundle webhook received: batch_id=%s, scripts=%d",
                     raw.get("batch_id", "?"), len(raw.get("scripts", [])))
        payload = ToolScriptBundlePayload.model_validate(raw)
        await container.agent_service.submit_script_bundle(payload)
    except Exception as exc:
        logger.error("submit_script_bundle failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WebhookAckResponse(status="ok", event_type="submit_script_bundle")


@router.post("/webhooks/elevenlabs", response_model=WebhookAckResponse)
async def elevenlabs_webhook(request: Request) -> WebhookAckResponse:
    container = request.app.state.container
    signature = (
        request.headers.get("elevenlabs-signature")
        or request.headers.get("x-elevenlabs-signature")
        or request.headers.get("signature")
    )
    if not signature:
        raise HTTPException(status_code=400, detail="Missing ElevenLabs webhook signature header.")

    raw_body = await request.body()
    try:
        event = await container.agent_service.handle_elevenlabs_webhook(raw_body, signature)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    event_type = (
        event.get("type")
        or event.get("event_type")
        or event.get("event", {}).get("type")
        or "elevenlabs_webhook"
    )
    return WebhookAckResponse(status="ok", event_type=str(event_type))


def _validate_bearer(authorization: str | None, expected_token: str | None, label: str) -> None:
    if request_should_bypass_auth():
        return
    if not expected_token:
        raise HTTPException(status_code=503, detail=f"{label} is not configured.")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or token != expected_token:
        raise HTTPException(status_code=401, detail=f"Unauthorized for {label}.")


_cached_env: str | None = None


def request_should_bypass_auth() -> bool:
    global _cached_env  # noqa: PLW0603
    if _cached_env is None:
        from brainrot_backend.config import Settings
        _cached_env = Settings().environment.lower()
    return _cached_env != "production"
