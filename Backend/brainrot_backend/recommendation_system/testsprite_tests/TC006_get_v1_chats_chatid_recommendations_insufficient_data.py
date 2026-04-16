import requests

BASE_URL = "http://localhost:8000"


def test_get_v1_chats_chatid_recommendations_insufficient_data():
    chat_id = None
    try:
        # Create a chat
        post_url = f"{BASE_URL}/v1/chats"
        post_payload = {"title": "Recs Test"}
        post_resp = requests.post(post_url, json=post_payload, timeout=30)
        assert post_resp.status_code == 200, f"Expected 200, got {post_resp.status_code}"
        post_json = post_resp.json()
        assert "chat" in post_json and "id" in post_json["chat"]
        chat_id = post_json["chat"]["id"]

        # Get recommendations for created chat
        get_url = f"{BASE_URL}/v1/chats/{chat_id}/recommendations"
        get_resp = requests.get(get_url, timeout=30)
        assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}"
        get_json = get_resp.json()

        # Verify response keys and values
        assert "chat_id" in get_json, "Missing chat_id in response"
        assert get_json["chat_id"] == chat_id, "chat_id mismatch in recommendations response"
        assert "has_enough_data" in get_json, "Missing has_enough_data in response"
        assert get_json["has_enough_data"] is False, "Expected has_enough_data to be False"
        assert "reels_tracked" in get_json, "Missing reels_tracked in response"
        assert "min_reels_required" in get_json, "Missing min_reels_required in response"
        assert isinstance(get_json["reels_tracked"], int), "reels_tracked is not int"
        assert isinstance(get_json["min_reels_required"], int), "min_reels_required is not int"
        assert get_json["reels_tracked"] < get_json["min_reels_required"], "reels_tracked should be less than min_reels_required"

    finally:
        if chat_id:
            try:
                del_url = f"{BASE_URL}/v1/chats/{chat_id}"
                requests.delete(del_url, timeout=30)
            except Exception:
                pass


test_get_v1_chats_chatid_recommendations_insufficient_data()