"""End-to-end smoke test for the SOURCE_UNAVAILABLE error path.

We simulate Firecrawl returning a 403 for a URL the user provided, then
drive the full BatchOrchestrator + Repository + EventBroker stack and confirm:

  1. The orchestrator marks the batch as FAILED.
  2. BatchRecord.error contains the friendly message that asks the user
     to try a different URL.
  3. An ERROR event is persisted with the SOURCE_UNAVAILABLE code,
     a user_message, and the offending URL so the frontend can render
     the dedicated UI for it.
  4. Transient backend-side issues (HTTP 429) are NOT classified as
     SOURCE_UNAVAILABLE so we never tell the user to swap URLs when the
     real problem is on our side.

Run with:

    uv run python scripts/verify_source_unavailable_flow.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx

from brainrot_backend.config import Settings
from brainrot_backend.core.models.domain import BatchItemRecord, BatchRecord
from brainrot_backend.core.models.enums import (
    BatchEventType,
    BatchItemStatus,
    BatchStatus,
    SourceKind,
)
from brainrot_backend.core.storage.memory import InMemoryRepository
from brainrot_backend.video_generator.integrations.firecrawl import (
    FirecrawlClient,
    SourceUnavailableError,
)
from brainrot_backend.video_generator.services.events import EventBroker
from brainrot_backend.video_generator.workers.orchestrator import BatchOrchestrator


class _StubBlobStore:
    async def upload_bytes(self, *args, **kwargs):  # pragma: no cover - not used here
        raise NotImplementedError


class _StubAgentService: ...
class _StubChatService: ...
class _StubAssetSelector: ...
class _StubRenderer: ...


async def _drive() -> int:
    settings = Settings(firecrawl_api_key="test-key", firecrawl_request_retries=1)
    repository = InMemoryRepository()
    events = EventBroker(repository)

    client = FirecrawlClient(settings)

    target_url = "https://news.example.com/blocked-article"

    async def fake_post(path: str, payload: dict):
        request = httpx.Request("POST", "https://api.firecrawl.dev/v2/scrape")
        response = httpx.Response(403, json={"error": "blocked"}, request=request)
        raise httpx.HTTPStatusError("blocked", request=request, response=response)

    client._post = fake_post  # type: ignore[method-assign]

    orchestrator = BatchOrchestrator(
        settings=settings,
        repository=repository,
        blob_store=_StubBlobStore(),
        events=events,
        firecrawl=client,
        agent_service=_StubAgentService(),
        chat_service=_StubChatService(),
        asset_selector=_StubAssetSelector(),
        renderer=_StubRenderer(),
    )

    batch = BatchRecord(
        source_kind=SourceKind.ARTICLE,
        source_url=target_url,
        requested_count=5,
    )
    await repository.create_batch(batch)
    items = [
        BatchItemRecord(batch_id=batch.id, item_index=index, status=BatchItemStatus.QUEUED)
        for index in range(5)
    ]
    await repository.create_batch_items(items)

    raised: Exception | None = None
    try:
        await orchestrator.run_batch(batch.id)
    except Exception as exc:
        raised = exc

    refreshed = await repository.get_batch(batch.id)
    assert refreshed is not None, "batch record should still exist"

    persisted_events = await repository.list_batch_events(batch.id, after_sequence=0)
    error_events = [e for e in persisted_events if e.event_type == BatchEventType.ERROR]

    print("=== SOURCE_UNAVAILABLE smoke test ===")
    print(f"raised exception in run_batch: {raised!r}")
    print(f"final batch status:            {refreshed.status}")
    print(f"final batch.error:             {refreshed.error}")
    print(f"persisted events:              {len(persisted_events)}")
    print(f"persisted ERROR events:        {len(error_events)}")
    if error_events:
        print("ERROR event payload:")
        print(json.dumps(error_events[-1].payload, indent=2, default=str))

    failures: list[str] = []
    if raised is not None:
        failures.append(
            f"orchestrator should swallow SourceUnavailableError, got {raised!r}"
        )
    if refreshed.status != BatchStatus.FAILED:
        failures.append(f"expected status FAILED, got {refreshed.status}")
    if not refreshed.error or "different URL" not in refreshed.error:
        failures.append(
            f"batch.error should include 'different URL', got: {refreshed.error!r}"
        )
    if not error_events:
        failures.append("expected at least one ERROR event")
    else:
        payload = error_events[-1].payload
        if payload.get("code") != "SOURCE_UNAVAILABLE":
            failures.append(f"expected code SOURCE_UNAVAILABLE, got {payload.get('code')!r}")
        if payload.get("url") != target_url:
            failures.append(f"expected url={target_url!r}, got {payload.get('url')!r}")
        if "user_message" not in payload:
            failures.append("expected user_message in ERROR payload")
        if payload.get("status_code") != 403:
            failures.append(f"expected status_code=403, got {payload.get('status_code')!r}")
        if payload.get("stage") != "ingest":
            failures.append(f"expected stage='ingest', got {payload.get('stage')!r}")

    rl_client = FirecrawlClient(Settings(firecrawl_api_key="test-key", firecrawl_request_retries=1))

    async def fake_post_429(path: str, payload: dict):
        request = httpx.Request("POST", "https://api.firecrawl.dev/v2/scrape")
        response = httpx.Response(429, json={"error": "rate limited"}, request=request)
        raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    rl_client._post = fake_post_429  # type: ignore[method-assign]
    saw_source_unavailable = False
    try:
        await rl_client._scrape_url("https://example.com/x", SourceKind.ARTICLE)
    except SourceUnavailableError:
        saw_source_unavailable = True
    except httpx.HTTPStatusError:
        pass
    if saw_source_unavailable:
        failures.append("HTTP 429 should NOT be converted to SOURCE_UNAVAILABLE")

    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("\nOK: SOURCE_UNAVAILABLE end-to-end flow verified.")
    return 0


def main() -> int:
    return asyncio.run(_drive())


if __name__ == "__main__":
    raise SystemExit(main())
