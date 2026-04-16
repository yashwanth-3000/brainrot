import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_batches_invalid_input_validation():
    url = f"{BASE_URL}/v1/batches"

    test_cases = [
        # (form_data, expected_status)
        ({}, 422),
        ({"source_url": "http://example.com", "count": "4"}, 422),
        ({"source_url": "http://example.com", "count": "16"}, 422),
        ({"count": "5"}, 422),
    ]

    headers = {
        "Accept": "application/json",
    }

    for form_data, expected_status in test_cases:
        try:
            response = requests.post(url, data=form_data, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            assert False, f"Request failed for form_data {form_data}: {e}"
        # Validate response status code
        assert response.status_code == expected_status, (
            f"Expected status {expected_status} but got {response.status_code} "
            f"for form_data {form_data} with response text: {response.text}"
        )
        # Validate response body is JSON with detail key on 422
        if expected_status == 422:
            try:
                json_resp = response.json()
            except ValueError:
                assert False, f"Response is not JSON for form_data {form_data}: {response.text}"
            assert "detail" in json_resp, f"'detail' key missing in response JSON for form_data {form_data}"

test_post_v1_batches_invalid_input_validation()