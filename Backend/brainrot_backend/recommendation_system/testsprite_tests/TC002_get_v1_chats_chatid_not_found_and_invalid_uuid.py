import requests

def test_get_v1_chats_chatid_not_found_and_invalid_uuid():
    base_url = "http://localhost:8000"
    headers = {"Accept": "application/json"}
    timeout = 30
    
    # Test invalid UUID format returns 422
    invalid_uuid = "not-a-uuid"
    url_invalid = f"{base_url}/v1/chats/{invalid_uuid}"
    response_invalid = requests.get(url_invalid, headers=headers, timeout=timeout)
    assert response_invalid.status_code == 422, f"Expected 422 for invalid UUID, got {response_invalid.status_code}"
    
    # Test non-existent but valid UUID returns 404
    non_existent_uuid = "00000000-0000-0000-0000-000000000000"
    url_non_existent = f"{base_url}/v1/chats/{non_existent_uuid}"
    response_non_existent = requests.get(url_non_existent, headers=headers, timeout=timeout)
    assert response_non_existent.status_code == 404, f"Expected 404 for non-existent UUID, got {response_non_existent.status_code}"

test_get_v1_chats_chatid_not_found_and_invalid_uuid()