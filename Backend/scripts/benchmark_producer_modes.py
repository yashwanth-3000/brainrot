from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from brainrot_backend.config import Settings
from brainrot_backend.core.models.domain import ScriptDraft
from brainrot_backend.video_generator.services.agents import _count_words, _script_quality_issues


MODES = ("direct_openai", "elevenlabs_native")


def parse_args() -> argparse.Namespace:
    settings = Settings()
    parser = argparse.ArgumentParser(description="Benchmark producer modes on the same source URL.")
    parser.add_argument("--source-url", required=True, help="URL to ingest and script.")
    parser.add_argument("--count", type=int, default=5, help="Number of scripts to request.")
    parser.add_argument("--port", type=int, default=8000, help="Port for the temporary backend server.")
    parser.add_argument("--timeout", type=int, default=240, help="Seconds to wait for scripts to become ready.")
    parser.add_argument(
        "--public-base-url",
        default=settings.public_base_url or "",
        help="Public HTTPS base URL that ElevenLabs can reach for tool callbacks.",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=MODES,
        default=list(MODES),
        help="Producer modes to benchmark.",
    )
    return parser.parse_args()


def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def benchmark_dir() -> Path:
    path = backend_root() / "data" / "benchmarks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
        return
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def wait_for_health(url: str, *, timeout: int) -> None:
    started_at = time.perf_counter()
    while time.perf_counter() - started_at < timeout:
        try:
            response = httpx.get(url, timeout=5.0)
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") == "ok":
                return
        except Exception:
            time.sleep(1.0)
    raise TimeoutError(f"Timed out waiting for health check: {url}")


def analyze_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    scripts = [item["script"] for item in items if item.get("script")]
    analyses: list[dict[str, Any]] = []
    for index, raw_script in enumerate(scripts, start=1):
        script = ScriptDraft.model_validate(raw_script)
        analyses.append(
            {
                "index": index,
                "title": script.title,
                "hook": script.hook,
                "word_count": _count_words(script.narration_text),
                "character_count": len(script.narration_text),
                "issues": _script_quality_issues(script),
                "source_facts_used": script.source_facts_used,
                "narration_text": script.narration_text,
            }
        )
    word_counts = [entry["word_count"] for entry in analyses]
    char_counts = [entry["character_count"] for entry in analyses]
    total_issue_count = sum(len(entry["issues"]) for entry in analyses)
    return {
        "script_count": len(analyses),
        "average_word_count": round(sum(word_counts) / len(word_counts), 1) if word_counts else 0,
        "average_character_count": round(sum(char_counts) / len(char_counts), 1) if char_counts else 0,
        "scripts_with_issues": sum(1 for entry in analyses if entry["issues"]),
        "issue_count": total_issue_count,
        "scripts": analyses,
    }


def run_mode(
    *,
    mode: str,
    source_url: str,
    count: int,
    port: int,
    timeout: int,
    public_base_url: str,
    timestamp: str,
) -> dict[str, Any]:
    if not public_base_url:
        raise RuntimeError("BRAINROT_PUBLIC_BASE_URL or --public-base-url is required for this benchmark.")

    local_base_url = f"http://127.0.0.1:{port}"
    log_path = benchmark_dir() / f"{timestamp}-{mode}.log"
    env = os.environ.copy()
    env["BRAINROT_PUBLIC_BASE_URL"] = public_base_url
    env["BRAINROT_PRODUCER_MODE"] = mode
    env["BRAINROT_SUPABASE_URL"] = ""
    env["BRAINROT_SUPABASE_SERVICE_ROLE_KEY"] = ""
    env["BRAINROT_SUPABASE_PUBLIC_URL"] = ""
    if mode == "elevenlabs_native":
        base_name = env.get("BRAINROT_PRODUCER_AGENT_NAME") or Settings().producer_agent_name
        env["BRAINROT_PRODUCER_AGENT_NAME"] = f"{base_name} Native Benchmark"

    with log_path.open("wb") as log_file:
        process = subprocess.Popen(
            ["uv", "run", "uvicorn", "brainrot_backend.main:app", "--host", "0.0.0.0", "--port", str(port)],
            cwd=backend_root(),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        try:
            wait_for_health(f"{local_base_url}/health", timeout=40)
            if mode == "elevenlabs_native":
                wait_for_health(f"{public_base_url.rstrip('/')}/health", timeout=40)

            with httpx.Client(base_url=local_base_url, timeout=httpx.Timeout(30.0, connect=10.0)) as client:
                bootstrap_started = time.perf_counter()
                bootstrap_response = client.post("/v1/agents/bootstrap")
                bootstrap_response.raise_for_status()
                bootstrap_elapsed = round(time.perf_counter() - bootstrap_started, 2)

                batch_started = time.perf_counter()
                create_response = client.post(
                    "/v1/batches",
                    data={
                        "source_url": source_url,
                        "count": str(count),
                    },
                )
                create_response.raise_for_status()
                envelope = create_response.json()
                batch_id = envelope["batch"]["id"]

                while time.perf_counter() - batch_started < timeout:
                    envelope = client.get(f"/v1/batches/{batch_id}").json()
                    batch = envelope["batch"]
                    items = envelope["items"]
                    producer_metrics = (batch.get("metadata") or {}).get("producer_metrics")
                    if producer_metrics and all(item.get("script") for item in items):
                        return {
                            "status": "scripts_ready",
                            "mode": mode,
                            "batch_id": batch_id,
                            "bootstrap_elapsed_seconds": bootstrap_elapsed,
                            "producer_metrics": producer_metrics,
                            "script_analysis": analyze_items(items),
                            "log_path": str(log_path),
                        }
                    if batch["status"] in {"failed", "partial_failed", "completed"} and not producer_metrics:
                        return {
                            "status": batch["status"],
                            "mode": mode,
                            "batch_id": batch_id,
                            "bootstrap_elapsed_seconds": bootstrap_elapsed,
                            "batch": batch,
                            "items": items,
                            "log_path": str(log_path),
                        }
                    time.sleep(2.0)

                return {
                    "status": "timeout",
                    "mode": mode,
                    "batch_id": batch_id,
                    "bootstrap_elapsed_seconds": bootstrap_elapsed,
                    "log_path": str(log_path),
                }
        finally:
            stop_process(process)


def main() -> int:
    args = parse_args()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    results: list[dict[str, Any]] = []
    for mode in args.modes:
        try:
            result = run_mode(
                mode=mode,
                source_url=args.source_url,
                count=args.count,
                port=args.port,
                timeout=args.timeout,
                public_base_url=args.public_base_url,
                timestamp=timestamp,
            )
        except Exception as exc:
            result = {
                "status": "error",
                "mode": mode,
                "error": str(exc),
            }
        results.append(result)
        if result.get("status") == "scripts_ready":
            printable = {
                "mode": mode,
                "status": result["status"],
                "batch_id": result["batch_id"],
                "producer_elapsed_seconds": result["producer_metrics"]["elapsed_seconds"],
                "attempt_count": result["producer_metrics"]["attempt_count"],
                "repair_count": result["producer_metrics"]["repair_count"],
                "scripts_with_issues": result["script_analysis"]["scripts_with_issues"],
                "average_word_count": result["script_analysis"]["average_word_count"],
                "average_character_count": result["script_analysis"]["average_character_count"],
            }
        else:
            printable = {
                "mode": mode,
                "status": result.get("status", "error"),
                "batch_id": result.get("batch_id"),
                "error": result.get("error") or result.get("batch", {}).get("error"),
                "log_path": result.get("log_path"),
            }
        print(json.dumps(printable, indent=2))

    summary_path = benchmark_dir() / f"{timestamp}-summary.json"
    summary_path.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
    print(f"Saved benchmark summary to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
