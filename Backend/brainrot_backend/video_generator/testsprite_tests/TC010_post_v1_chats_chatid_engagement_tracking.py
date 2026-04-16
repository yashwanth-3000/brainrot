import requests
import uuid
import time

BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 30

def create_chat():
    url = f"{BASE_URL}/v1/chats"
    payload = {
        "title": f"Test Chat {uuid.uuid4()}",
        "source": "test_source"
    }
    resp = requests.post(url, json=payload, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    chat_id = data.get("chat", {}).get("id")
    assert chat_id is not None, f"Response JSON does not contain 'chat.id': {data}"
    return chat_id

def delete_chat(chat_id):
    # The API schema does not specify deleting chats.
    # If there was an endpoint to delete, implement it here.
    pass

def post_engagement(chat_id, payload):
    url = f"{BASE_URL}/v1/chats/{chat_id}/engagement"
    return requests.post(url, json=payload, headers=HEADERS, timeout=TIMEOUT)

def test_post_v1_chats_chatid_engagement_tracking():
    chat_id = None
    try:
        # Create chat to test against
        chat_id = create_chat()

        # 1. Valid engagement event post
        valid_payload = {
            "viewer_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "item_id": str(uuid.uuid4()),
            "watch_time_seconds": 30,
            "completion_ratio": 0.75,
            "liked": True,
            "skipped": False,
            "muted": False,
            "info_opened": True
        }
        r = post_engagement(chat_id, valid_payload)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

        # 2. Duplicate engagement post (should deduplicate silently and return 200)
        r_dup = post_engagement(chat_id, valid_payload)
        assert r_dup.status_code == 200, f"Expected 200 on duplicate, got {r_dup.status_code}"

        # 3. Missing required fields (e.g. missing viewer_id)
        invalid_payload = {
            "session_id": str(uuid.uuid4()),
            "item_id": str(uuid.uuid4()),
            "watch_time_seconds": 10,
            "completion_ratio": 0.5
        }
        r_missing = post_engagement(chat_id, invalid_payload)
        assert r_missing.status_code == 422, f"Expected 422 for missing fields, got {r_missing.status_code}"

        # 4. Non-existent chat_id
        fake_chat_id = str(uuid.uuid4())
        r_notfound = post_engagement(fake_chat_id, valid_payload)
        assert r_notfound.status_code == 404, f"Expected 404 for non-existent chat, got {r_notfound.status_code}"

    finally:
        if chat_id:
            delete_chat(chat_id)

test_post_v1_chats_chatid_engagement_tracking()
