import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
BEARER_TOKEN = "Bearer testtoken123"  # replace with a valid token if available

headers = {"Content-Type": "application/json", "Authorization": BEARER_TOKEN}

def test_get_v1_chats_list_and_get_single():
    chat_id = None

    # Step 1: Create chat via POST /v1/chats with JSON including required 'source'
    try:
        post_url = f"{BASE_URL}/v1/chats"
        post_payload = {"title": "List Test", "source": {"url": "https://example.com"}}
        post_resp = requests.post(post_url, json=post_payload, headers=headers, timeout=TIMEOUT)
        assert post_resp.status_code == 200, f"POST /v1/chats failed with status {post_resp.status_code}"
        post_json = post_resp.json()
        assert "chat" in post_json, "Response JSON missing 'chat' key"
        assert "id" in post_json["chat"], "'chat' object missing 'id'"
        chat_id = post_json["chat"]["id"]
        assert isinstance(chat_id, str) and chat_id != "", "chat_id is not a non-empty string"

        # Step 2: GET /v1/chats — verify chat appears in items by matching item['id'] == chat_id
        get_list_url = f"{BASE_URL}/v1/chats"
        get_list_resp = requests.get(get_list_url, headers=headers, timeout=TIMEOUT)
        assert get_list_resp.status_code == 200, f"GET /v1/chats failed with status {get_list_resp.status_code}"
        get_list_json = get_list_resp.json()
        assert "items" in get_list_json, "Response JSON missing 'items' key"
        items = get_list_json["items"]
        assert isinstance(items, list), "'items' is not a list"
        found = any(item.get("id") == chat_id for item in items)
        assert found, f"Chat ID {chat_id} not found in /v1/chats items"

        # Step 3: GET /v1/chats/{chat_id} — verify the chat matches
        get_single_url = f"{BASE_URL}/v1/chats/{chat_id}"
        get_single_resp = requests.get(get_single_url, headers=headers, timeout=TIMEOUT)
        assert get_single_resp.status_code == 200, f"GET /v1/chats/{chat_id} failed with status {get_single_resp.status_code}"
        get_single_json = get_single_resp.json()
        assert "chat" in get_single_json, "Response JSON missing 'chat' key"
        single_chat = get_single_json["chat"]
        assert isinstance(single_chat, dict), "'chat' is not a dictionary"
        assert "id" in single_chat, "'chat' missing 'id'"
        assert single_chat["id"] == chat_id, f"Chat ID mismatch: expected {chat_id}, got {single_chat['id']}"
    finally:
        if chat_id:
            # Cleanup: delete the chat via DELETE /v1/chats/{chat_id} if such endpoint exists
            # Not specified in PRD - so skip cleanup as no info is given
            pass

test_get_v1_chats_list_and_get_single()