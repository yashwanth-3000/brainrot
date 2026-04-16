import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_chats_chatid_engagement_errors():
    # Part 1: POST /v1/chats/00000000-0000-0000-0000-000000000000/engagement with valid body returns 404
    url_error = f"{BASE_URL}/v1/chats/00000000-0000-0000-0000-000000000000/engagement"
    payload_error = {"item_id":"a","viewer_id":"b","session_id":"c"}
    try:
        response_error = requests.post(url_error, json=payload_error, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request failed for error path 1: {e}"
    assert response_error.status_code == 404, f"Expected 404 for non-existent chat_id engagement post, got {response_error.status_code}"

    # Part 2: Create a chat, then POST engagement with missing item_id should return 422
    chat_create_url = f"{BASE_URL}/v1/chats"
    chat_payload = {"title": "Engagement Error Test"}
    try:
        chat_response = requests.post(chat_create_url, json=chat_payload, timeout=TIMEOUT)
        chat_response.raise_for_status()
        chat_json = chat_response.json()
        chat_id = chat_json['chat']['id']
    except (requests.RequestException, KeyError) as e:
        assert False, f"Failed to create chat or parse chat_id: {e}"
    
    engagement_url = f"{BASE_URL}/v1/chats/{chat_id}/engagement"
    engagement_payload_missing_item_id = {"viewer_id":"x","session_id":"y"}

    try:
        response_422 = requests.post(engagement_url, json=engagement_payload_missing_item_id, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request failed for error path 2: {e}"
    finally:
        # Cleanup: delete the created chat to maintain test hygiene
        try:
            del_url = f"{BASE_URL}/v1/chats/{chat_id}"
            # DELETE method not detailed in PRD, skip if unsupported
            requests.delete(del_url, timeout=TIMEOUT)
        except Exception:
            pass

    assert response_422.status_code == 422, f"Expected 422 for missing item_id in engagement post, got {response_422.status_code}"

test_post_v1_chats_chatid_engagement_errors()