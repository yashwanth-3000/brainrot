from fastapi.testclient import TestClient

from brainrot_backend.config import Settings
from brainrot_backend.main import create_app
from brainrot_backend.models.domain import AgentConfigRecord
from brainrot_backend.models.enums import AgentRole, BatchItemStatus


def test_health_endpoint():
    app = create_app(
        Settings(
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
        assert payload["batch"]["producer_agent_config_id"] is not None
        assert payload["batch"]["narrator_agent_config_id"] is not None

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


def test_chat_aggregates_multiple_batches(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        temp_dir=tmp_path / "tmp",
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
