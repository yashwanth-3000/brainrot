import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_chats_chatid_engagement_valid():
    chat_id = None
    try:
        # Step 1: Create a chat
        create_chat_url = f"{BASE_URL}/v1/chats"
        create_chat_payload = {"title": "Engagement Test", "source": "unit_test"}
        create_resp = requests.post(create_chat_url, json=create_chat_payload, timeout=TIMEOUT)
        assert create_resp.status_code == 200, f"Expected 200 on chat creation, got {create_resp.status_code}"
        create_data = create_resp.json()
        assert "chat_id" in create_data, "chat_id not found in response"
        chat_id = create_data["chat_id"]

        # Step 2: Post engagement for the created chat
        engagement_url = f"{BASE_URL}/v1/chats/{chat_id}/engagement"
        engagement_payload = {
            "item_id": str(uuid.uuid4()),
            "viewer_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "watch_time_seconds": 25.0,
            "completion_ratio": 0.8,
            "liked": True
        }
        engagement_resp = requests.post(engagement_url, json=engagement_payload, timeout=TIMEOUT)
        assert engagement_resp.status_code == 200, f"Expected 200 on engagement post, got {engagement_resp.status_code}"
        engagement_data = engagement_resp.json()
        assert "engagement" in engagement_data and "id" in engagement_data["engagement"], "Engagement id not found in response"

    finally:
        # Cleanup: delete the chat to avoid test pollution if such endpoint exists
        if chat_id:
            try:
                requests.delete(f"{BASE_URL}/v1/chats/{chat_id}", timeout=TIMEOUT)
            except Exception:
                pass

test_post_v1_chats_chatid_engagement_valid()
