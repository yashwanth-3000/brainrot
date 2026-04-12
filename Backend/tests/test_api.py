import pytest
from fastapi.testclient import TestClient

from brainrot_backend.config import Settings
from brainrot_backend.main import create_app
from brainrot_backend.shared.models.domain import AgentConfigRecord, ScriptDraft
from brainrot_backend.shared.models.enums import AgentRole, BatchItemStatus


def test_health_endpoint():
    app = create_app(
        Settings(
            storage_backend="memory",
            supabase_url=None,
            supabase_service_role_key=None,
            supabase_public_url=None,
        )
    )
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_create_batch_and_upload_asset(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        temp_dir=tmp_path / "tmp",
        storage_backend="memory",
        supabase_url=None,
        supabase_service_role_key=None,
        supabase_public_url=None,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        app.state.container.batch_service._schedule = lambda *args, **kwargs: None
        repository = app.state.container.repository
        import asyncio

        asyncio.run(
            repository.upsert_agent_config(
                AgentConfigRecord(
                    role=AgentRole.PRODUCER,
                    name="Producer",
                    agent_id="producer-agent",
                )
            )
        )
        asyncio.run(
            repository.upsert_agent_config(
                AgentConfigRecord(
                    role=AgentRole.NARRATOR,
                    name="Narrator",
                    agent_id="narrator-agent",
                )
            )
        )

        asset_response = client.post(
            "/v1/assets/upload",
            data={"kind": "gameplay", "tags": "fast,parkour", "metadata_json": "{}"},
            files={"file": ("clip.mp4", b"fake-video", "video/mp4")},
        )
        assert asset_response.status_code == 200
        assert asset_response.json()["asset"]["kind"] == "gameplay"

        chat_response = client.post(
            "/v1/chats",
            json={"title": "Research chat", "source_url": "https://example.com/blog/test-post"},
        )
        assert chat_response.status_code == 200
        chat_id = chat_response.json()["chat"]["id"]

        batch_response = client.post(
            "/v1/batches",
            data={
                "chat_id": chat_id,
                "source_url": "https://example.com/blog/test-post",
                "count": "5",
            },
        )
        assert batch_response.status_code == 200
        payload = batch_response.json()
        assert payload["batch"]["requested_count"] == 5
        assert payload["batch"]["chat_id"] == chat_id
        assert len(payload["items"]) == 5
        assert payload["batch"]["producer_agent_config_id"] is None
        assert payload["batch"]["narrator_agent_config_id"] is None

        first_item_id = payload["items"][0]["id"]
        asyncio.run(
            repository.update_batch_item(
                first_item_id,
                status=BatchItemStatus.UPLOADED,
                output_url="file:///tmp/example.mp4",
                render_metadata={"subtitle_style_label": "Single Word Pop"},
            )
        )

        asyncio.run(app.state.container.chat_service.refresh_chat_summary(chat_id))

        chat_list_response = client.get("/v1/chats")
        assert chat_list_response.status_code == 200
        assert chat_list_response.json()["items"][0]["id"] == chat_id

        chat_detail_response = client.get(f"/v1/chats/{chat_id}")
        assert chat_detail_response.status_code == 200
        assert chat_detail_response.json()["chat"]["id"] == chat_id

        chat_assets_response = client.get(f"/v1/chats/{chat_id}/shorts")
        assert chat_assets_response.status_code == 200
        chat_payload = chat_assets_response.json()
        assert chat_payload["chat_id"] == chat_id
        assert len(chat_payload["items"]) == 1
        assert chat_payload["items"][0]["batch_id"] == payload["batch"]["id"]
        assert chat_payload["items"][0]["item_id"] == first_item_id


def test_get_batch_item_video_falls_back_to_local_render_when_batch_record_is_missing(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        temp_dir=tmp_path / "tmp",
        storage_backend="memory",
        supabase_url=None,
        supabase_service_role_key=None,
        supabase_public_url=None,
    )
    app = create_app(settings)
    batch_id = "batch-local"
    item_id = "item-local"
    render_path = settings.data_dir / settings.final_render_bucket / batch_id / f"{item_id}.mp4"
    render_path.parent.mkdir(parents=True, exist_ok=True)
    render_path.write_bytes(b"fake-mp4")

    with TestClient(app) as client:
        response = client.get(f"/v1/batches/{batch_id}/items/{item_id}/video")

    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp4"
    assert response.content == b"fake-mp4"


def test_forced_supabase_storage_requires_credentials():
    app = create_app(
        Settings(
            storage_backend="supabase",
            supabase_url=None,
            supabase_service_role_key=None,
            supabase_public_url=None,
        )
    )

    with pytest.raises(RuntimeError, match="BRAINROT_STORAGE_BACKEND=supabase requires"):
        with TestClient(app):
            pass


def test_chat_aggregates_multiple_batches(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        temp_dir=tmp_path / "tmp",
        storage_backend="memory",
        supabase_url=None,
        supabase_service_role_key=None,
        supabase_public_url=None,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        app.state.container.batch_service._schedule = lambda *args, **kwargs: None
        repository = app.state.container.repository
        chat_service = app.state.container.chat_service
        import asyncio

        asyncio.run(
            repository.upsert_agent_config(
                AgentConfigRecord(
                    role=AgentRole.PRODUCER,
                    name="Producer",
                    agent_id="producer-agent",
                )
            )
        )
        asyncio.run(
            repository.upsert_agent_config(
                AgentConfigRecord(
                    role=AgentRole.NARRATOR,
                    name="Narrator",
                    agent_id="narrator-agent",
                )
            )
        )

        chat_response = client.post("/v1/chats", json={"title": "Library chat"})
        assert chat_response.status_code == 200
        chat_id = chat_response.json()["chat"]["id"]

        batch_one = client.post(
            "/v1/batches",
            data={
                "chat_id": chat_id,
                "source_url": "https://example.com/first",
                "title_hint": "First source",
                "count": "5",
            },
        ).json()
        batch_two = client.post(
            "/v1/batches",
            data={
                "chat_id": chat_id,
                "source_url": "https://example.com/second",
                "title_hint": "Second source",
                "count": "5",
            },
        ).json()

        first_batch_id = batch_one["batch"]["id"]
        second_batch_id = batch_two["batch"]["id"]
        first_item_id = batch_one["items"][0]["id"]
        second_item_id = batch_two["items"][0]["id"]
        third_item_id = batch_two["items"][1]["id"]

        asyncio.run(
            repository.update_batch_item(
                first_item_id,
                status=BatchItemStatus.UPLOADED,
                output_url="file:///tmp/first.mp4",
            )
        )
        asyncio.run(
            repository.update_batch_item(
                batch_one["items"][1]["id"],
                status=BatchItemStatus.FAILED,
                error="render failed",
            )
        )
        asyncio.run(repository.update_batch(first_batch_id, status="partial_failed"))

        asyncio.run(
            repository.update_batch_item(
                second_item_id,
                status=BatchItemStatus.UPLOADED,
                output_url="file:///tmp/second.mp4",
            )
        )
        asyncio.run(
            repository.update_batch_item(
                third_item_id,
                status=BatchItemStatus.UPLOADED,
                output_url="file:///tmp/third.mp4",
            )
        )
        asyncio.run(repository.update_batch(second_batch_id, status="completed"))
        asyncio.run(chat_service.refresh_chat_summary(chat_id))

        chat_list_response = client.get("/v1/chats")
        assert chat_list_response.status_code == 200
        chat_summary = chat_list_response.json()["items"][0]
        assert chat_summary["id"] == chat_id
        assert chat_summary["total_runs"] == 2
        assert chat_summary["total_exported"] == 3
        assert chat_summary["total_failed"] == 1
        assert chat_summary["last_status"] == "completed"

        chat_detail_response = client.get(f"/v1/chats/{chat_id}")
        assert chat_detail_response.status_code == 200
        assert chat_detail_response.json()["chat"]["title"] == "Second source"

        chat_assets_response = client.get(f"/v1/chats/{chat_id}/shorts")
        assert chat_assets_response.status_code == 200
        asset_payload = chat_assets_response.json()
        assert asset_payload["chat"]["id"] == chat_id
        assert len(asset_payload["items"]) == 3


def test_public_chat_list_hides_empty_chats(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        temp_dir=tmp_path / "tmp",
        storage_backend="memory",
        supabase_url=None,
        supabase_service_role_key=None,
        supabase_public_url=None,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        app.state.container.batch_service._schedule = lambda *args, **kwargs: None
        repository = app.state.container.repository
        chat_service = app.state.container.chat_service
        import asyncio

        asyncio.run(
            repository.upsert_agent_config(
                AgentConfigRecord(
                    role=AgentRole.PRODUCER,
                    name="Producer",
                    agent_id="producer-agent",
                )
            )
        )
        asyncio.run(
            repository.upsert_agent_config(
                AgentConfigRecord(
                    role=AgentRole.NARRATOR,
                    name="Narrator",
                    agent_id="narrator-agent",
                )
            )
        )

        empty_chat_response = client.post("/v1/chats", json={"title": "Empty chat"})
        assert empty_chat_response.status_code == 200

        exported_chat_response = client.post("/v1/chats", json={"title": "Exported chat"})
        assert exported_chat_response.status_code == 200
        exported_chat_id = exported_chat_response.json()["chat"]["id"]

        batch_payload = client.post(
            "/v1/batches",
            data={
                "chat_id": exported_chat_id,
                "source_url": "https://example.com/exported",
                "title_hint": "Exported source",
                "count": "5",
            },
        ).json()

        asyncio.run(
            repository.update_batch_item(
                batch_payload["items"][0]["id"],
                status=BatchItemStatus.UPLOADED,
                output_url="file:///tmp/exported.mp4",
            )
        )
        asyncio.run(repository.update_batch(batch_payload["batch"]["id"], status="completed"))
        asyncio.run(chat_service.refresh_chat_summary(exported_chat_id))

        chat_list_response = client.get("/v1/chats")
        assert chat_list_response.status_code == 200
        items = chat_list_response.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == exported_chat_id


def test_chat_recommendations_prefer_high_retention_formats(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        temp_dir=tmp_path / "tmp",
        storage_backend="memory",
        supabase_url=None,
        supabase_service_role_key=None,
        supabase_public_url=None,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        app.state.container.batch_service._schedule = lambda *args, **kwargs: None
        repository = app.state.container.repository
        chat_service = app.state.container.chat_service
        import asyncio

        asyncio.run(
            repository.upsert_agent_config(
                AgentConfigRecord(
                    role=AgentRole.PRODUCER,
                    name="Producer",
                    agent_id="producer-agent",
                )
            )
        )
        asyncio.run(
            repository.upsert_agent_config(
                AgentConfigRecord(
                    role=AgentRole.NARRATOR,
                    name="Narrator",
                    agent_id="narrator-agent",
                )
            )
        )

        chat_response = client.post("/v1/chats", json={"title": "Retention chat"})
        assert chat_response.status_code == 200
        chat_id = chat_response.json()["chat"]["id"]

        batch_payload = client.post(
            "/v1/batches",
            data={
                "chat_id": chat_id,
                "source_url": "https://example.com/retention",
                "title_hint": "Retention source",
                "count": "5",
            },
        ).json()

        first_item = batch_payload["items"][0]
        second_item = batch_payload["items"][1]
        third_item = batch_payload["items"][2]

        asyncio.run(
            repository.update_batch_item(
                first_item["id"],
                status=BatchItemStatus.UPLOADED,
                output_url="file:///tmp/high-retention.mp4",
                render_metadata={
                    "subtitle_style_label": "Single Word Pop",
                    "subtitle_font_name": "Komika Axis",
                    "gameplay_asset_path": "gameplay/roblox/roblox_clip_08.mp4",
                },
                script=ScriptDraft(
                    title="The hidden risk in AI agents",
                    hook="The hidden risk in AI agents",
                    narration_text="The hidden risk in AI agents is not just model quality. It is the invisible operational drag teams discover too late.",
                    caption_text="The hidden risk in AI agents",
                    estimated_seconds=25.0,
                    visual_beats=[],
                    music_tags=[],
                    gameplay_tags=[],
                    source_facts_used=["AI agent operations can create hidden overhead."],
                ),
            )
        )
        asyncio.run(
            repository.update_batch_item(
                second_item["id"],
                status=BatchItemStatus.UPLOADED,
                output_url="file:///tmp/low-retention.mp4",
                render_metadata={
                    "subtitle_style_label": "Karaoke Sweep",
                    "subtitle_font_name": "Montserrat ExtraBold",
                    "gameplay_asset_path": "gameplay/minecraft/minecraft_clip_04.mp4",
                },
                script=ScriptDraft(
                    title="How this workflow is built",
                    hook="How this workflow is built",
                    narration_text="Here is how the workflow is built from source ingest through render.",
                    caption_text="How this workflow is built",
                    estimated_seconds=25.0,
                    visual_beats=[],
                    music_tags=[],
                    gameplay_tags=[],
                    source_facts_used=["The workflow runs from ingest to render."],
                ),
            )
        )
        asyncio.run(
            repository.update_batch_item(
                third_item["id"],
                status=BatchItemStatus.UPLOADED,
                output_url="file:///tmp/third-retention.mp4",
                render_metadata={
                    "subtitle_style_label": "Single Word Pop",
                    "subtitle_font_name": "Komika Axis",
                    "gameplay_asset_path": "gameplay/roblox/roblox_clip_10.mp4",
                },
                script=ScriptDraft(
                    title="Why creators keep using this workflow",
                    hook="Why creators keep using this workflow",
                    narration_text="Creators keep using this workflow because one source can turn into a repeatable batch of shorts.",
                    caption_text="Why creators keep using this workflow",
                    estimated_seconds=24.0,
                    visual_beats=[],
                    music_tags=[],
                    gameplay_tags=[],
                    source_facts_used=["One source can become a batch of shorts."],
                ),
            )
        )
        asyncio.run(repository.update_batch(batch_payload["batch"]["id"], status="completed"))
        asyncio.run(chat_service.refresh_chat_summary(chat_id))

        current_session_id = "page-session-1"
        for payload in (
            {
                "item_id": first_item["id"],
                "viewer_id": "viewer-a",
                "session_id": "session-a",
                "watch_time_seconds": 24.0,
                "completion_ratio": 0.96,
                "max_progress_seconds": 24.0,
                "replay_count": 1,
                "unmuted": True,
                "liked": True,
                "metadata": {"page_session_id": current_session_id},
            },
            {
                "item_id": second_item["id"],
                "viewer_id": "viewer-b",
                "session_id": "session-b",
                "watch_time_seconds": 3.0,
                "completion_ratio": 0.12,
                "max_progress_seconds": 3.0,
                "skipped_early": True,
                "metadata": {"page_session_id": current_session_id},
            },
            {
                "item_id": third_item["id"],
                "viewer_id": "viewer-c",
                "session_id": "session-c",
                "watch_time_seconds": 21.0,
                "completion_ratio": 0.875,
                "max_progress_seconds": 21.0,
                "info_opened": True,
                "open_clicked": True,
                "metadata": {"page_session_id": current_session_id},
            },
        ):
            response = client.post(f"/v1/chats/{chat_id}/engagement", json=payload)
            assert response.status_code == 200

        stale_response = client.post(
            f"/v1/chats/{chat_id}/engagement",
            json={
                "item_id": second_item["id"],
                "viewer_id": "viewer-z",
                "session_id": "session-z",
                "watch_time_seconds": 19.0,
                "completion_ratio": 0.79,
                "max_progress_seconds": 19.0,
                "metadata": {"page_session_id": "page-session-old"},
            },
        )
        assert stale_response.status_code == 200

        recommendation_response = client.get(
            f"/v1/chats/{chat_id}/recommendations",
            params={"session_id": current_session_id},
        )
        assert recommendation_response.status_code == 200
        recommendation = recommendation_response.json()

        assert recommendation["chat_id"] == chat_id
        assert recommendation["has_enough_data"] is True
        assert recommendation["total_sessions"] == 3
        assert recommendation["reels_tracked"] == 3
        assert recommendation["session_id"] == current_session_id
        assert recommendation["top_gameplay"][0]["label"] == "Roblox"
        assert recommendation["top_caption_styles"][0]["label"] == "Single Word Pop · Komika Axis"
        assert recommendation["top_text_styles"][0]["label"] == "warning-style"
        retention_by_title = {
            item["title"]: item["watch_time_seconds"]
            for item in recommendation["retention_summary"]
        }
        assert retention_by_title["The hidden risk in AI agents"] == 24.0
        assert retention_by_title["How this workflow is built"] == 3.0
        assert retention_by_title["Why creators keep using this workflow"] == 21.0
        assert "Roblox" in recommendation["generation_prompt"]
