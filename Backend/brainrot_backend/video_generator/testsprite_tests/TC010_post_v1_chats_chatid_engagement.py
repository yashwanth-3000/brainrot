import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_chats_chatid_engagement():
    chat_id = None
    headers = {"Content-Type": "application/json"}
    try:
        # Step 1: Create a chat
        create_chat_payload = {"title": "Engagement Test", "source_metadata": {}}
        create_resp = requests.post(f"{BASE_URL}/v1/chats", json=create_chat_payload, headers=headers, timeout=TIMEOUT)
        assert create_resp.status_code == 200, f"Expected 200 but got {create_resp.status_code}"
        create_data = create_resp.json()
        assert "chat_id" in create_data, "Response JSON missing 'chat_id'"
        chat_id = create_data["chat_id"]
        assert isinstance(chat_id, str) and len(chat_id) > 0, "Invalid chat_id extracted"

        # Step 2: Post engagement tracking with valid data
        engagement_payload = {
            "item_id": str(uuid.uuid4()),
            "viewer_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "watch_time_seconds": 30.0,
            "completion_ratio": 0.75,
            "liked": True
        }
        engagement_resp = requests.post(f"{BASE_URL}/v1/chats/{chat_id}/engagement", json=engagement_payload, headers=headers, timeout=TIMEOUT)
        assert engagement_resp.status_code == 200, f"Expected 200 but got {engagement_resp.status_code}"
        engagement_data = engagement_resp.json()
        assert "engagement" in engagement_data and "id" in engagement_data["engagement"], "Response JSON missing 'engagement' or 'engagement.id'"

        # Step 3: Test with non-existent chat_id -> expect 404
        non_existent_chat_id = "00000000-0000-0000-0000-000000000000"
        engagement_resp_404 = requests.post(f"{BASE_URL}/v1/chats/{non_existent_chat_id}/engagement", json=engagement_payload, headers=headers, timeout=TIMEOUT)
        assert engagement_resp_404.status_code == 404, f"Expected 404 for non-existent chat_id but got {engagement_resp_404.status_code}"

        # Step 4: Test with missing required field 'item_id' -> expect 422
        invalid_payload = {
            # "item_id" missing
            "viewer_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "watch_time_seconds": 30.0,
            "completion_ratio": 0.75,
            "liked": True
        }
        engagement_resp_422 = requests.post(f"{BASE_URL}/v1/chats/{chat_id}/engagement", json=invalid_payload, headers=headers, timeout=TIMEOUT)
        assert engagement_resp_422.status_code == 422, f"Expected 422 for missing required field but got {engagement_resp_422.status_code}"

    finally:
        if chat_id:
            # Cleanup: Delete the created chat if API supports DELETE (not specified in PRD)
            # Since DELETE is not defined in PRD, we skip deletion.
            pass

test_post_v1_chats_chatid_engagement()
