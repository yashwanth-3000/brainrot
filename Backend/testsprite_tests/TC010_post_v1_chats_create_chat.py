import requests

def test_post_v1_chats_create_chat():
    base_url = "http://localhost:8000"
    url = f"{base_url}/v1/chats"
    payload = {"title": "Full Backend Test Chat"}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        assert response.status_code == 200, f"Expected status 200 but got {response.status_code}"

        json_data = response.json()
        assert "chat" in json_data, "'chat' key not found in response JSON"
        chat_info = json_data["chat"]
        assert "id" in chat_info, "'id' key not found in chat"
        chat_id = chat_info["id"]
        assert isinstance(chat_id, str) and chat_id.strip() != "", "chat_id is not a non-empty string"

    finally:
        # Cleanup: delete the created chat if possible
        try:
            if 'chat_id' in locals() and chat_id:
                delete_url = f"{base_url}/v1/chats/{chat_id}"
                requests.delete(delete_url, timeout=30)
        except Exception:
            pass

test_post_v1_chats_create_chat()