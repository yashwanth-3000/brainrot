from __future__ import annotations

import asyncio
import re
import time
from contextlib import suppress
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from brainrot_backend.config import Settings
from brainrot_backend.shared.models.domain import IngestedSource
from brainrot_backend.shared.models.enums import SourceKind


CONTENT_HINTS = (
    "/blog",
    "/post",
    "/article",
    "/articles",
    "/docs",
    "/research",
    "/paper",
    "/insights",
)
EXCLUDED_HINTS = (
    "/tag",
    "/tags",
    "/category",
    "/categories",
    "/privacy",
    "/terms",
    "/legal",
    "/author",
    "/authors",
    "/archive",
    "/search",
    "/login",
    "/signup",
)

type ProgressCallback = Callable[[dict[str, object]], Awaitable[None]]


class FirecrawlClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def ingest(
        self,
        *,
        source_url: str | None,
        source_kind: SourceKind,
        uploaded_file_path: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> IngestedSource:
        started_at = time.perf_counter()
        await self._report_progress(
            progress_callback,
            stage="ingest",
            source="firecrawl",
            message=f"Starting Firecrawl ingest for {source_kind.value}.",
            elapsed_seconds=0.0,
            source_url=source_url,
        )
        if source_kind == SourceKind.PDF_UPLOAD:
            if uploaded_file_path is None:
                raise ValueError("PDF upload source requires an uploaded file path.")
            return await self._parse_local_pdf(self._resolve_uploaded_file_path(uploaded_file_path))
        if source_kind == SourceKind.PDF_URL:
            return await self._scrape_url(
                source_url or "",
                SourceKind.PDF_URL,
                progress_callback=progress_callback,
                started_at=started_at,
            )
        if source_kind == SourceKind.WEBSITE:
            return await self._ingest_site(
                source_url or "",
                progress_callback=progress_callback,
                started_at=started_at,
            )
        return await self._scrape_url(
            source_url or "",
            SourceKind.ARTICLE,
            progress_callback=progress_callback,
            started_at=started_at,
        )

    async def _scrape_url(
        self,
        url: str,
        source_kind: SourceKind,
        *,
        progress_callback: ProgressCallback | None = None,
        started_at: float | None = None,
    ) -> IngestedSource:
        await self._report_progress(
            progress_callback,
            stage="ingest",
            source="firecrawl",
            message=f"Scraping {url} via Firecrawl.",
            elapsed_seconds=self._elapsed(started_at),
            source_kind=source_kind.value,
            url=url,
        )
        primary_payload = {
            "url": url,
            "formats": ["markdown", "summary"],
            "maxAge": self.settings.firecrawl_scrape_max_age_ms,
        }
        fallback_payload = {
            "url": url,
            "formats": ["markdown"],
            "maxAge": max(self.settings.firecrawl_scrape_max_age_ms, 600_000),
        }
        try:
            data = await self._await_with_progress(
                self._post("v2/scrape", primary_payload),
                progress_callback=progress_callback,
                started_at=started_at,
                message="Firecrawl scrape request is still running.",
                source_kind=source_kind.value,
                url=url,
            )
        except Exception as exc:
            await self._report_progress(
                progress_callback,
                stage="ingest",
                source="firecrawl",
                message="Primary scrape timed out or failed. Retrying with markdown-only scrape.",
                elapsed_seconds=self._elapsed(started_at),
                source_kind=source_kind.value,
                url=url,
                error=str(exc),
            )
            data = await self._await_with_progress(
                self._post("v2/scrape", fallback_payload),
                progress_callback=progress_callback,
                started_at=started_at,
                message="Firecrawl scrape request is still running.",
                source_kind=source_kind.value,
                url=url,
            )
        payload = self._unwrap_data(data)
        markdown = payload.get("markdown") or payload.get("content") or ""
        metadata = dict(payload.get("metadata") or {})
        if payload.get("summary"):
            metadata.setdefault("source_summary", payload["summary"])
        normalized_source_url = metadata.get("sourceURL") or metadata.get("url") or url
        title = metadata.get("title") or payload.get("title") or url
        await self._report_progress(
            progress_callback,
            stage="ingest",
            source="firecrawl",
            message=f"Scrape completed for {title}.",
            elapsed_seconds=self._elapsed(started_at),
            source_kind=source_kind.value,
            url=str(normalized_source_url),
            char_count=len(markdown),
        )
        return IngestedSource(
            source_kind=source_kind,
            original_url=str(normalized_source_url),
            title=title,
            markdown=markdown,
            normalized_urls=[str(normalized_source_url)],
            metadata=metadata,
        )

    async def _ingest_site(
        self,
        url: str,
        *,
        progress_callback: ProgressCallback | None = None,
        started_at: float | None = None,
    ) -> IngestedSource:
        await self._report_progress(
            progress_callback,
            stage="ingest",
            source="firecrawl",
            message="Mapping website URLs with Firecrawl.",
            elapsed_seconds=self._elapsed(started_at),
            url=url,
        )
        try:
            mapped = await self._await_with_progress(
                self._post("v2/map", {"url": url, "includeSubdomains": False}),
                progress_callback=progress_callback,
                started_at=started_at,
                message="Firecrawl site mapping request is still running.",
                url=url,
            )
        except Exception as exc:
            await self._report_progress(
                progress_callback,
                stage="ingest",
                source="firecrawl",
                message="Site mapping failed. Falling back to a direct scrape of the source URL.",
                elapsed_seconds=self._elapsed(started_at),
                url=url,
                error=str(exc),
            )
            return await self._scrape_url(
                url,
                SourceKind.WEBSITE,
                progress_callback=progress_callback,
                started_at=started_at,
            )
        raw_urls = self._unwrap_data(mapped)
        if isinstance(raw_urls, dict):
            candidates = raw_urls.get("links") or raw_urls.get("urls") or []
        else:
            candidates = raw_urls

        ranked = rank_site_urls(url, extract_candidate_urls(candidates))
        selected = ranked[: self.settings.firecrawl_site_url_limit]
        if not selected:
            selected = [url]

        markdown_chunks: list[str] = []
        metadata = {"selected_urls": selected, "url_count": len(candidates)}
        await self._report_progress(
            progress_callback,
            stage="ingest",
            source="firecrawl",
            message=f"Mapped {len(candidates)} candidate URLs and selected {len(selected)} for ingestion.",
            elapsed_seconds=self._elapsed(started_at),
            selected_url_count=len(selected),
            candidate_url_count=len(candidates),
        )

        try:
            await self._report_progress(
                progress_callback,
                stage="ingest",
                source="firecrawl",
                message="Starting Firecrawl crawl job for selected URLs.",
                elapsed_seconds=self._elapsed(started_at),
                selected_url_count=len(selected),
            )
            crawl = await self._post(
                "v2/crawl",
                {
                    "url": url,
                    "limit": len(selected),
                    "includePaths": [urlparse(link).path for link in selected if urlparse(link).path],
                    "scrapeOptions": {"formats": ["markdown"]},
                },
            )
            crawl_result = await self._poll_crawl(
                crawl,
                progress_callback=progress_callback,
                started_at=started_at,
            )
            documents = self._unwrap_data(crawl_result)
            if isinstance(documents, list):
                markdown_chunks.extend(
                    (doc.get("markdown") or "").strip() for doc in documents if doc.get("markdown")
                )
            await self._report_progress(
                progress_callback,
                stage="ingest",
                source="firecrawl",
                message=f"Firecrawl crawl completed with {len(markdown_chunks)} document(s).",
                elapsed_seconds=self._elapsed(started_at),
                document_count=len(markdown_chunks),
            )
        except Exception as exc:
            await self._report_progress(
                progress_callback,
                stage="ingest",
                source="firecrawl",
                message="Crawl job failed, falling back to per-URL scraping.",
                elapsed_seconds=self._elapsed(started_at),
                error=str(exc),
            )
            for index, selected_url in enumerate(selected, start=1):
                await self._report_progress(
                    progress_callback,
                    stage="ingest",
                    source="firecrawl",
                    message=f"Fallback scraping URL {index}/{len(selected)}.",
                    elapsed_seconds=self._elapsed(started_at),
                    url=selected_url,
                    fallback_index=index,
                    fallback_total=len(selected),
                )
                scraped = await self._scrape_url(
                    selected_url,
                    SourceKind.ARTICLE,
                    progress_callback=progress_callback,
                    started_at=started_at,
                )
                markdown_chunks.append(scraped.markdown)

        if not markdown_chunks:
            raise RuntimeError("Firecrawl did not return content for the requested website.")

        return IngestedSource(
            source_kind=SourceKind.WEBSITE,
            original_url=url,
            title=urlparse(url).netloc,
            markdown="\n\n".join(markdown_chunks),
            normalized_urls=selected,
            metadata=metadata,
        )

    async def _poll_crawl(
        self,
        crawl_response: dict,
        *,
        progress_callback: ProgressCallback | None = None,
        started_at: float | None = None,
    ) -> dict:
        job_id = crawl_response.get("id") or crawl_response.get("jobId")
        if not job_id:
            return await self._hydrate_paginated_result(crawl_response)

        attempts = 0
        while attempts < self.settings.firecrawl_poll_attempts:
            attempts += 1
            data = await self._get(f"v2/crawl/{job_id}")
            status = data.get("status")
            await self._report_progress(
                progress_callback,
                stage="ingest",
                source="firecrawl",
                message=f"Firecrawl crawl job {job_id} is {status or 'pending'} (poll {attempts}/{self.settings.firecrawl_poll_attempts}).",
                elapsed_seconds=self._elapsed(started_at),
                job_id=str(job_id),
                poll_attempt=attempts,
                poll_limit=self.settings.firecrawl_poll_attempts,
                job_status=status,
            )
            if status in {"completed", "done", "success"}:
                return await self._hydrate_paginated_result(data)
            if status in {"failed", "error"}:
                raise RuntimeError(f"Firecrawl crawl failed: {data}")
            await asyncio.sleep(self.settings.firecrawl_poll_interval_seconds)
        raise TimeoutError(f"Timed out waiting for Firecrawl crawl job {job_id}.")

    async def _parse_local_pdf(self, file_path: Path) -> IngestedSource:
        try:
            import pdfplumber  # type: ignore
        except ImportError as exc:
            raise RuntimeError("pdfplumber is required for local PDF upload parsing.") from exc

        with pdfplumber.open(file_path) as pdf:
            pages = [(page.extract_text() or "") for page in pdf.pages]
            page_count = len(pdf.pages)
        markdown = "\n\n".join(text.strip() for text in pages if text.strip())
        title = file_path.name or "uploaded.pdf"
        return IngestedSource(
            source_kind=SourceKind.PDF_UPLOAD,
            title=title,
            markdown=markdown,
            normalized_urls=[],
            metadata={"page_count": page_count, "local_path": str(file_path.relative_to(self.settings.project_root))},
        )

    async def _post(self, path: str, payload: dict[str, Any]) -> dict:
        return await self._request_json("POST", path, payload=payload)

    async def _get(self, path: str) -> dict:
        return await self._request_json("GET", path)

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict:
        if not self.settings.firecrawl_enabled:
            raise RuntimeError("Firecrawl API key is not configured.")
        headers = {"Authorization": f"Bearer {self.settings.firecrawl_api_key}"}
        request_url = path if path.startswith("http://") or path.startswith("https://") else None
        timeout = httpx.Timeout(
            self.settings.firecrawl_request_timeout_seconds,
            connect=self.settings.firecrawl_connect_timeout_seconds,
        )
        retryable_status_codes = {408, 409, 425, 429, 500, 502, 503, 504}
        last_error: Exception | None = None

        for attempt in range(1, max(1, self.settings.firecrawl_request_retries) + 1):
            try:
                async with httpx.AsyncClient(
                    base_url=None if request_url else self.settings.firecrawl_base_url,
                    timeout=timeout,
                ) as client:
                    response = await client.request(
                        method,
                        request_url or path,
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code not in retryable_status_codes or attempt >= self.settings.firecrawl_request_retries:
                    raise
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt >= self.settings.firecrawl_request_retries:
                    raise

            await asyncio.sleep(self.settings.firecrawl_retry_backoff_seconds * attempt)

        assert last_error is not None
        raise last_error

    async def _hydrate_paginated_result(self, payload: dict) -> dict:
        combined = dict(payload)
        documents = list(payload.get("data") or [])
        next_url = payload.get("next")
        while next_url:
            page = await self._get(str(next_url))
            documents.extend(page.get("data") or [])
            next_url = page.get("next")
        if documents:
            combined["data"] = documents
        return combined

    def _resolve_uploaded_file_path(self, file_path: str) -> Path:
        path = Path(file_path)
        if path.is_absolute():
            return path
        return (self.settings.project_root / path).resolve()

    @staticmethod
    def _unwrap_data(payload: dict):
        return payload.get("data", payload)

    @staticmethod
    def _elapsed(started_at: float | None) -> float | None:
        if started_at is None:
            return None
        return round(time.perf_counter() - started_at, 1)

    async def _report_progress(
        self,
        progress_callback: ProgressCallback | None,
        **payload: object,
    ) -> None:
        if progress_callback is None:
            return
        await progress_callback(payload)

    async def _await_with_progress(
        self,
        awaitable,
        *,
        progress_callback: ProgressCallback | None,
        started_at: float | None,
        message: str,
        **payload: object,
    ):
        task = asyncio.create_task(awaitable)
        heartbeat = 0
        try:
            while True:
                try:
                    return await asyncio.wait_for(
                        asyncio.shield(task),
                        timeout=self.settings.progress_heartbeat_seconds,
                    )
                except TimeoutError:
                    heartbeat += 1
                    await self._report_progress(
                        progress_callback,
                        stage="ingest",
                        source="firecrawl",
                        message=message,
                        elapsed_seconds=self._elapsed(started_at),
                        heartbeat=heartbeat,
                        **payload,
                    )
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task


def rank_site_urls(root_url: str, urls: list[str]) -> list[str]:
    root = urlparse(root_url)
    seen: set[str] = set()
    scored: list[tuple[int, str]] = []

    for raw_url in urls:
        if not raw_url:
            continue
        full_url = urljoin(root_url, raw_url)
        parsed = urlparse(full_url)
        if parsed.netloc != root.netloc:
            continue
        normalized = parsed._replace(fragment="", query="").geturl().rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        path = parsed.path.lower()

        score = 0
        if any(hint in path for hint in CONTENT_HINTS):
            score += 5
        if re.search(r"/\d{4}/\d{2}/", path):
            score += 2
        if path.count("/") >= 2:
            score += 1
        if any(hint in path for hint in EXCLUDED_HINTS):
            score -= 8
        if path in {"", "/"}:
            score -= 2

        scored.append((score, normalized))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [url for score, url in scored if score >= 0]


def extract_candidate_urls(raw_links: list[Any]) -> list[str]:
    urls: list[str] = []
    for item in raw_links:
        if isinstance(item, str):
            urls.append(item)
            continue
        if isinstance(item, dict):
            url = item.get("url") or item.get("sourceURL") or item.get("sourceUrl")
            if isinstance(url, str):
                urls.append(url)
    return urls
