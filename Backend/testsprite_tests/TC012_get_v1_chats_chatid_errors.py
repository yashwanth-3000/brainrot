import requests

def test_get_v1_chats_chatid_errors():
    base_url = "http://localhost:8000"
    timeout = 30
    headers = {}

    # Test invalid UUID format returns 422
    invalid_uuid = "invalid-uuid"
    url_invalid_uuid = f"{base_url}/v1/chats/{invalid_uuid}"
    response_invalid_uuid = requests.get(url_invalid_uuid, headers=headers, timeout=timeout)
    assert response_invalid_uuid.status_code == 422, f"Expected status 422 for invalid UUID but got {response_invalid_uuid.status_code}"

    # Test valid UUID not found returns 404
    not_found_uuid = "00000000-0000-0000-0000-000000000000"
    url_not_found_uuid = f"{base_url}/v1/chats/{not_found_uuid}"
    response_not_found_uuid = requests.get(url_not_found_uuid, headers=headers, timeout=timeout)
    assert response_not_found_uuid.status_code == 404, f"Expected status 404 for non-existent chat but got {response_not_found_uuid.status_code}"

test_get_v1_chats_chatid_errors()