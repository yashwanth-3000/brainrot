from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse
from starlette.background import BackgroundTask


async def _close_remote_stream(response: httpx.Response, client: httpx.AsyncClient) -> None:
    await response.aclose()
    await client.aclose()


async def video_response_from_output_url(
    output_url: str,
    *,
    range_header: str | None = None,
    if_range_header: str | None = None,
):
    if output_url.startswith("file://"):
        local_path = Path(urlparse(output_url).path)
        if not local_path.exists():
            raise HTTPException(status_code=404, detail="Video file is missing.")
        return FileResponse(local_path, media_type="video/mp4", filename=local_path.name)

    upstream_headers: dict[str, str] = {}
    if range_header:
        upstream_headers["range"] = range_header
    if if_range_header:
        upstream_headers["if-range"] = if_range_header

    client = httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(120.0, connect=10.0),
    )
    upstream = await client.send(client.build_request("GET", output_url, headers=upstream_headers), stream=True)

    if upstream.status_code >= 400:
        try:
            response_bytes = await upstream.aread()
        finally:
            await upstream.aclose()
            await client.aclose()
        return Response(
            content=response_bytes,
            status_code=upstream.status_code,
            media_type=upstream.headers.get("content-type") or "text/plain",
            headers={
                key: value
                for key, value in upstream.headers.items()
                if key.lower() in {"cache-control", "content-length", "content-range", "accept-ranges", "etag", "last-modified"}
            },
        )

    headers: dict[str, str] = {}
    for header_name in (
        "content-length",
        "content-range",
        "accept-ranges",
        "cache-control",
        "etag",
        "last-modified",
    ):
        header_value = upstream.headers.get(header_name)
        if header_value:
            headers[header_name] = header_value

    return StreamingResponse(
        upstream.aiter_bytes(),
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type") or "video/mp4",
        headers=headers,
        background=BackgroundTask(_close_remote_stream, upstream, client),
    )
