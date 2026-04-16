import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_get_v1_chats_chatid_recommendations_not_found():
    non_existent_chat_id = "00000000-0000-0000-0000-000000000000"
    url = f"{BASE_URL}/v1/chats/{non_existent_chat_id}/recommendations"
    try:
        response = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"
    assert response.status_code == 404, f"Expected status code 404 but got {response.status_code}"

test_get_v1_chats_chatid_recommendations_not_found()