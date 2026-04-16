import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
HEADERS = {"Content-Type": "application/json"}

def test_post_v1_chats_engagement_errors():
    # Part 1: POST engagement to non-existent chat (should return 404)
    invalid_chat_id = "00000000-0000-0000-0000-000000000000"
    url_invalid = f"{BASE_URL}/v1/chats/{invalid_chat_id}/engagement"
    payload_invalid = {"item_id":"a","viewer_id":"b","session_id":"c"}
    response_invalid = requests.post(url_invalid, json=payload_invalid, headers=HEADERS, timeout=TIMEOUT)
    assert response_invalid.status_code == 404
    
    # Part 2: Create a chat, then POST engagement missing 'item_id' (should return 422)
    url_create_chat = f"{BASE_URL}/v1/chats"
    chat_payload = {"title": "Test Chat for Engagement Errors"}
    response_chat = requests.post(url_create_chat, json=chat_payload, headers=HEADERS, timeout=TIMEOUT)
    assert response_chat.status_code == 200
    chat_json = response_chat.json()
    assert "chat" in chat_json and "id" in chat_json["chat"]
    chat_id = chat_json["chat"]["id"]
    assert isinstance(chat_id, str) and chat_id != ""

    url_engagement = f"{BASE_URL}/v1/chats/{chat_id}/engagement"
    engagement_payload_missing_item_id = {"viewer_id":"x","session_id":"y"}
    
    try:
        response_engagement = requests.post(url_engagement, json=engagement_payload_missing_item_id, headers=HEADERS, timeout=TIMEOUT)
        assert response_engagement.status_code == 422
    finally:
        # cleanup: delete the chat
        del_url = f"{BASE_URL}/v1/chats/{chat_id}"
        requests.delete(del_url, timeout=TIMEOUT)

test_post_v1_chats_engagement_errors()