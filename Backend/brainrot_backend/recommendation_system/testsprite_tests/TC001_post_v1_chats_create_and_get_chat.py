import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_chats_create_and_get_chat():
    chat_title = "Rec Test Chat"
    headers = {"Content-Type": "application/json"}

    # Create a chat (POST /v1/chats)
    post_url = f"{BASE_URL}/v1/chats"
    post_payload = {"title": chat_title, "source": {"type": "url", "url": "https://example.com"}}
    post_response = requests.post(post_url, json=post_payload, headers=headers, timeout=TIMEOUT)
    assert post_response.status_code == 200, f"Expected 200 on chat creation, got {post_response.status_code}"
    post_json = post_response.json()
    assert "chat_id" in post_json and isinstance(post_json["chat_id"], str), "Response JSON missing 'chat_id' string"
    chat_id = post_json["chat_id"]

    # Retrieve the created chat (GET /v1/chats/{chat_id})
    get_chat_url = f"{BASE_URL}/v1/chats/{chat_id}"
    get_chat_response = requests.get(get_chat_url, headers=headers, timeout=TIMEOUT)
    assert get_chat_response.status_code == 200, f"Expected 200 on get chat, got {get_chat_response.status_code}"
    get_chat_json = get_chat_response.json()
    assert "chat" in get_chat_json and isinstance(get_chat_json["chat"], dict), "Response JSON missing 'chat' dict on get"
    chat_fetched = get_chat_json["chat"]
    assert chat_fetched.get("chat_id") == chat_id, "Chat ID mismatch on get"
    assert chat_fetched.get("title") == chat_title, "Chat title mismatch on get"

    # Verify the chat appears in the chats list (GET /v1/chats)
    get_chats_url = f"{BASE_URL}/v1/chats"
    get_chats_response = requests.get(get_chats_url, headers=headers, timeout=TIMEOUT)
    assert get_chats_response.status_code == 200, f"Expected 200 on get chats list, got {get_chats_response.status_code}"
    get_chats_json = get_chats_response.json()
    assert "items" in get_chats_json and isinstance(get_chats_json["items"], list), "Response JSON missing 'items' list"
    chat_ids = [chat.get("chat_id") for chat in get_chats_json["items"] if isinstance(chat, dict) and "chat_id" in chat]
    assert chat_id in chat_ids, "Created chat_id not found in chats items list"

# Cleanup delete is not supported, so no delete call here

test_post_v1_chats_create_and_get_chat()
