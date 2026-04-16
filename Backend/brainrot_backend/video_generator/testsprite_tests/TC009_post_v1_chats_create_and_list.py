import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_chats_create_and_list():
    headers = {
        "Content-Type": "application/json"
    }
    chat_id = None
    try:
        # Step 1: POST /v1/chats with JSON body {'title': 'Test Chat'}
        post_data = {"title": "Test Chat"}
        response_post = requests.post(f"{BASE_URL}/v1/chats", json=post_data, headers=headers, timeout=TIMEOUT)
        response_post.raise_for_status()
        json_post = response_post.json()
        assert "chat_id" in json_post, f"Expected 'chat_id' key in response JSON, got: {json_post}"
        chat_id = json_post["chat_id"]

        # Step 2: GET /v1/chats to list all chats
        response_get_list = requests.get(f"{BASE_URL}/v1/chats", headers=headers, timeout=TIMEOUT)
        response_get_list.raise_for_status()
        json_list = response_get_list.json()
        assert "items" in json_list and isinstance(json_list["items"], list), \
            f"Expected 'items' list in response, got: {json_list}"
        # Verify the created chat appears in the list by matching 'id'
        found_chat = any(item.get("id") == chat_id for item in json_list["items"])
        assert found_chat, f"Created chat id '{chat_id}' not found in chat list."

        # Step 3: GET /v1/chats/{chat_id} to retrieve single chat
        response_get_single = requests.get(f"{BASE_URL}/v1/chats/{chat_id}", headers=headers, timeout=TIMEOUT)
        response_get_single.raise_for_status()
        json_single = response_get_single.json()
        assert "chat" in json_single, f"Expected 'chat' key in response JSON, got: {json_single}"
        assert json_single["chat"].get("id") == chat_id, \
            f"Chat id mismatch, expected '{chat_id}', got: {json_single['chat'].get('id')}"

    finally:
        if chat_id:
            try:
                requests.delete(f"{BASE_URL}/v1/chats/{chat_id}", headers=headers, timeout=TIMEOUT)
            except Exception:
                pass

test_post_v1_chats_create_and_list()
