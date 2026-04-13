import asyncio

import httpx

from brainrot_backend.config import Settings
from brainrot_backend.video_generator.integrations.firecrawl import FirecrawlClient
from brainrot_backend.core.models.domain import IngestedSource
from brainrot_backend.core.models.enums import SourceKind


def test_scrape_url_falls_back_to_markdown_only_after_timeout():
    settings = Settings(firecrawl_api_key="test-key")
    client = FirecrawlClient(settings)
    attempts: list[dict] = []
    progress_messages: list[str] = []

    async def fake_post(path: str, payload: dict):
        attempts.append(payload)
        if len(attempts) == 1:
            raise httpx.ReadTimeout("timed out")
        return {
            "data": {
                "markdown": "# Content Hub\n\nBody",
                "metadata": {"title": "Content Hub | Devpost", "url": "https://devpost.com/software/content-hub"},
            }
        }

    async def progress_callback(payload: dict[str, object]) -> None:
        message = payload.get("message")
        if isinstance(message, str):
            progress_messages.append(message)

    client._post = fake_post  # type: ignore[method-assign]

    source = asyncio.run(
        client._scrape_url(
            "https://devpost.com/software/content-hub",
            SourceKind.ARTICLE,
            progress_callback=progress_callback,
        )
    )

    assert source.title == "Content Hub | Devpost"
    assert source.markdown.startswith("# Content Hub")
    assert attempts[0]["formats"] == ["markdown", "summary"]
    assert attempts[1]["formats"] == ["markdown"]
    assert any("markdown-only scrape" in message for message in progress_messages)


def test_ingest_site_falls_back_to_direct_scrape_when_mapping_fails():
    settings = Settings(firecrawl_api_key="test-key")
    client = FirecrawlClient(settings)
    progress_messages: list[str] = []

    async def fake_post(path: str, payload: dict):
        raise httpx.ReadTimeout("map timed out")

    async def fake_scrape_url(*args, **kwargs):
        return IngestedSource(
            source_kind=SourceKind.WEBSITE,
            original_url="https://example.com",
            title="example.com",
            markdown="site content",
            normalized_urls=["https://example.com"],
            metadata={},
        )

    async def progress_callback(payload: dict[str, object]) -> None:
        message = payload.get("message")
        if isinstance(message, str):
            progress_messages.append(message)

    client._post = fake_post  # type: ignore[method-assign]
    client._scrape_url = fake_scrape_url  # type: ignore[method-assign]

    source = asyncio.run(
        client._ingest_site(
            "https://example.com",
            progress_callback=progress_callback,
        )
    )

    assert source.source_kind == SourceKind.WEBSITE
    assert source.markdown == "site content"
    assert any("direct scrape" in message for message in progress_messages)
