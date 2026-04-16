import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_get_v1_batches_batchid_uuid_validation_and_not_found():
    headers = {"Accept": "application/json"}

    # Test case 1: Invalid UUID format
    invalid_uuid = "not-a-uuid-string"
    url_invalid = f"{BASE_URL}/v1/batches/{invalid_uuid}"
    try:
        response_invalid = requests.get(url_invalid, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request to invalid UUID failed with exception: {e}"
    assert response_invalid.status_code == 422, f"Expected 422 for invalid UUID, got {response_invalid.status_code}"
    try:
        json_invalid = response_invalid.json()
    except ValueError:
        assert False, "Response for invalid UUID is not valid JSON"
    assert "detail" in json_invalid, "Response JSON for invalid UUID does not contain 'detail' key"

    # Test case 2: Valid UUID but non-existent in DB
    non_existent_uuid = "00000000-0000-0000-0000-000000000000"
    url_not_found = f"{BASE_URL}/v1/batches/{non_existent_uuid}"
    try:
        response_not_found = requests.get(url_not_found, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request to non-existent UUID failed with exception: {e}"
    assert response_not_found.status_code == 404, f"Expected 404 for non-existent UUID, got {response_not_found.status_code}"
    try:
        json_not_found = response_not_found.json()
    except ValueError:
        assert False, "Response for non-existent UUID is not valid JSON"
    assert "detail" in json_not_found, "Response JSON for non-existent UUID does not contain 'detail' key"

test_get_v1_batches_batchid_uuid_validation_and_not_found()