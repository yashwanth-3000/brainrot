import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
HEADERS_JSON = {"Content-Type": "application/json"}

def test_post_v1_chats_engagement_and_recommendations():
    chat_id = None
    try:
        # Step 1: Create chat
        url_create_chat = f"{BASE_URL}/v1/chats"
        payload_create_chat = {"title": "E2E Test", "source": "test-source"}
        response_create_chat = requests.post(url_create_chat, json=payload_create_chat, timeout=TIMEOUT)
        assert response_create_chat.status_code == 200, f"Expected 200 but got {response_create_chat.status_code}"
        json_create_chat = response_create_chat.json()
        assert "chat_id" in json_create_chat and isinstance(json_create_chat["chat_id"], str) and json_create_chat["chat_id"], "Response JSON missing or invalid 'chat_id' key"
        chat_id = json_create_chat["chat_id"]

        # Step 2: POST engagement
        url_engagement = f"{BASE_URL}/v1/chats/{chat_id}/engagement"
        payload_engagement = {
            "item_id": "11111111-1111-1111-1111-111111111111",
            "viewer_id": "22222222-2222-2222-2222-222222222222",
            "session_id": "33333333-3333-3333-3333-333333333333",
            "watch_time_seconds": 30.0,
            "completion_ratio": 0.8,
            "liked": True
        }
        response_engagement = requests.post(url_engagement, json=payload_engagement, timeout=TIMEOUT)
        assert response_engagement.status_code == 200, f"Expected 200 but got {response_engagement.status_code}"

        # Step 3: GET recommendations with session_id query param
        url_recommendations = f"{BASE_URL}/v1/chats/{chat_id}/recommendations?session_id={payload_engagement['session_id']}"
        response_recommendations = requests.get(url_recommendations, timeout=TIMEOUT)
        # According to PRD a 200 or 404 can be returned; here we expect 200 since chat exists
        assert response_recommendations.status_code == 200, f"Expected 200 but got {response_recommendations.status_code}"
        json_recommendations = response_recommendations.json()
        assert "has_enough_data" in json_recommendations, "Response JSON missing 'has_enough_data' key"
        assert isinstance(json_recommendations["has_enough_data"], bool), "'has_enough_data' is not boolean"

    finally:
        # Cleanup: delete the chat if possible
        if chat_id:
            try:
                requests.delete(f"{BASE_URL}/v1/chats/{chat_id}", timeout=TIMEOUT)
            except Exception:
                pass

test_post_v1_chats_engagement_and_recommendations()