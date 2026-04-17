import asyncio

import httpx
import pytest

from brainrot_backend.config import Settings
from brainrot_backend.video_generator.integrations.firecrawl import (
    FirecrawlClient,
    SourceUnavailableError,
)
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
                "markdown": (
                    "# Content Hub\n\n" + "This is the long-form Devpost project description. " * 20
                ),
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


def _http_status_error(status_code: int, body: dict | None = None) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://api.firecrawl.dev/v2/scrape")
    response = httpx.Response(status_code, json=body or {}, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


def test_scrape_url_raises_source_unavailable_on_403():
    settings = Settings(firecrawl_api_key="test-key")
    client = FirecrawlClient(settings)

    async def fake_post(path: str, payload: dict):
        raise _http_status_error(403, {"error": "blocked"})

    client._post = fake_post  # type: ignore[method-assign]

    with pytest.raises(SourceUnavailableError) as exc_info:
        asyncio.run(
            client._scrape_url(
                "https://news.example.com/locked",
                SourceKind.ARTICLE,
            )
        )
    error = exc_info.value
    assert error.code == "SOURCE_UNAVAILABLE"
    assert error.status_code == 403
    assert error.url == "https://news.example.com/locked"
    assert "different URL" in str(error)
    payload = error.to_event_payload()
    assert payload["code"] == "SOURCE_UNAVAILABLE"
    assert payload["status_code"] == 403
    assert "try again with a different url" in payload["user_message"].lower()


def test_scrape_url_raises_source_unavailable_on_dns_error_code():
    settings = Settings(firecrawl_api_key="test-key")
    client = FirecrawlClient(settings)

    async def fake_post(path: str, payload: dict):
        raise _http_status_error(500, {"errorCode": "SCRAPE_DNS_RESOLUTION_ERROR"})

    client._post = fake_post  # type: ignore[method-assign]

    with pytest.raises(SourceUnavailableError) as exc_info:
        asyncio.run(
            client._scrape_url(
                "https://this-domain-does-not-exist.invalid",
                SourceKind.ARTICLE,
            )
        )
    assert exc_info.value.firecrawl_code == "SCRAPE_DNS_RESOLUTION_ERROR"
    assert "domain could not be resolved" in str(exc_info.value)


def test_scrape_url_raises_source_unavailable_on_empty_markdown():
    settings = Settings(firecrawl_api_key="test-key")
    client = FirecrawlClient(settings)

    async def fake_post(path: str, payload: dict):
        return {
            "data": {
                "markdown": "",
                "metadata": {"title": "Empty"},
            }
        }

    client._post = fake_post  # type: ignore[method-assign]

    with pytest.raises(SourceUnavailableError) as exc_info:
        asyncio.run(
            client._scrape_url(
                "https://blank.example.com/",
                SourceKind.ARTICLE,
            )
        )
    assert "no readable content" in str(exc_info.value)


def test_scrape_url_raises_source_unavailable_on_anti_bot_wall():
    settings = Settings(firecrawl_api_key="test-key")
    client = FirecrawlClient(settings)
    bot_page = (
        "Just a moment...\n\n"
        "Please enable JavaScript and cookies to continue.\n\n"
        "Cloudflare is checking your browser before access. " * 5
    )

    async def fake_post(path: str, payload: dict):
        return {
            "data": {
                "markdown": bot_page,
                "metadata": {"title": "Just a moment"},
            }
        }

    client._post = fake_post  # type: ignore[method-assign]

    with pytest.raises(SourceUnavailableError) as exc_info:
        asyncio.run(
            client._scrape_url(
                "https://protected.example.com/",
                SourceKind.ARTICLE,
            )
        )
    assert "blocking automated access" in str(exc_info.value)


def test_scrape_url_raises_source_unavailable_on_metadata_4xx():
    settings = Settings(firecrawl_api_key="test-key")
    client = FirecrawlClient(settings)

    async def fake_post(path: str, payload: dict):
        return {
            "data": {
                "markdown": "x" * 600,
                "metadata": {"title": "Not Found", "statusCode": 404},
            }
        }

    client._post = fake_post  # type: ignore[method-assign]

    with pytest.raises(SourceUnavailableError) as exc_info:
        asyncio.run(
            client._scrape_url(
                "https://broken.example.com/missing",
                SourceKind.ARTICLE,
            )
        )
    assert exc_info.value.status_code == 404


def test_scrape_url_does_not_treat_rate_limit_as_source_unavailable():
    """Rate limits, auth failures, and quota errors are our problem, not the URL's."""
    settings = Settings(firecrawl_api_key="test-key", firecrawl_request_retries=1)
    client = FirecrawlClient(settings)

    async def fake_post(path: str, payload: dict):
        raise _http_status_error(429, {"error": "rate limited"})

    client._post = fake_post  # type: ignore[method-assign]

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(
            client._scrape_url(
                "https://example.com/article",
                SourceKind.ARTICLE,
            )
        )


def test_source_unavailable_error_payload_serializes_for_event():
    error = SourceUnavailableError(
        url="https://example.com/x",
        reason="the site refused our scraping request (HTTP 403)",
        status_code=403,
    )
    payload = error.to_event_payload()
    assert payload["code"] == "SOURCE_UNAVAILABLE"
    assert payload["url"] == "https://example.com/x"
    assert payload["status_code"] == 403
    assert "different URL" in payload["message"]
    assert payload["user_message"].endswith("with a different URL.")
