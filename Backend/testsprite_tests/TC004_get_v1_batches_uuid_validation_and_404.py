import requests

def test_get_v1_batches_uuid_validation_and_404():
    base_url = "http://localhost:8000"
    timeout = 30

    # 1. GET /v1/batches/not-a-uuid → expect 422 (invalid UUID)
    url_invalid_uuid = f"{base_url}/v1/batches/not-a-uuid"
    try:
        response_invalid_uuid = requests.get(url_invalid_uuid, timeout=timeout)
    except requests.RequestException as e:
        assert False, f"Request to {url_invalid_uuid} failed: {e}"
    else:
        assert response_invalid_uuid.status_code == 422, (
            f"Expected status 422 for invalid UUID, got {response_invalid_uuid.status_code}, "
            f"response: {response_invalid_uuid.text}"
        )

    # 2. GET /v1/batches/00000000-0000-0000-0000-000000000000 → expect 404 (valid UUID but not found)
    valid_but_not_found_uuid = "00000000-0000-0000-0000-000000000000"
    url_not_found = f"{base_url}/v1/batches/{valid_but_not_found_uuid}"
    try:
        response_not_found = requests.get(url_not_found, timeout=timeout)
    except requests.RequestException as e:
        assert False, f"Request to {url_not_found} failed: {e}"
    else:
        assert response_not_found.status_code == 404, (
            f"Expected status 404 for valid but non-existent UUID, got {response_not_found.status_code}, "
            f"response: {response_not_found.text}"
        )

test_get_v1_batches_uuid_validation_and_404()