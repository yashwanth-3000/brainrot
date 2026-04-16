import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_get_v1_chats_chatid_shorts_empty():
    chat_id = None
    try:
        # Create a chat
        post_url = f"{BASE_URL}/v1/chats"
        post_payload = {"title": "Shorts Test"}
        post_resp = requests.post(post_url, json=post_payload, timeout=TIMEOUT)
        assert post_resp.status_code == 200, f"POST /v1/chats failed with status {post_resp.status_code}"
        post_json = post_resp.json()
        assert "chat" in post_json and "id" in post_json["chat"], "Response missing chat.id"
        chat_id = post_json["chat"]["id"]

        # GET /v1/chats/{chat_id}/shorts
        get_url = f"{BASE_URL}/v1/chats/{chat_id}/shorts"
        get_resp = requests.get(get_url, timeout=TIMEOUT)
        assert get_resp.status_code == 200, f"GET /v1/chats/{chat_id}/shorts failed with status {get_resp.status_code}"
        get_json = get_resp.json()
        assert "chat_id" in get_json and get_json["chat_id"] == chat_id, "chat_id mismatch in response"
        assert "items" in get_json and isinstance(get_json["items"], list), "items missing or not a list"
        assert len(get_json["items"]) == 0, "Expected empty items list for new chat with no batches"
    finally:
        if chat_id:
            # Clean up: delete the created chat if API supports DELETE; if not, this can be omitted or adjusted
            # No DELETE endpoint specified in PRD, so skip deletion
            pass

test_get_v1_chats_chatid_shorts_empty()