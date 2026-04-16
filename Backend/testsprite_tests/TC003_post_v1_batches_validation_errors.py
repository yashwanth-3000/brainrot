import requests

def test_post_v1_batches_validation_errors():
    base_url = "http://localhost:8000"
    url = f"{base_url}/v1/batches"
    timeout = 30

    test_data = [
        ({}, 422),
        ({"source_url": "http://x.com", "count": "4"}, 422),  # count < 5
        ({"source_url": "http://x.com", "count": "16"}, 422), # count > 15
        ({"count": "5"}, 422)  # no source_url
    ]

    headers = {
        "Accept": "application/json"
    }

    for data, expected_status in test_data:
        try:
            response = requests.post(url, data=data, headers=headers, timeout=timeout)
        except requests.RequestException as e:
            assert False, f"Request failed with exception: {e}"

        assert response.status_code == expected_status, (
            f"Expected status {expected_status} but got {response.status_code} for data: {data}"
        )

test_post_v1_batches_validation_errors()