import requests

def test_get_v1_batches_batchid_status_notfound():
    base_url = "http://localhost:8000"
    non_existent_batch_id = "nonexistentbatchid1234567890"
    url = f"{base_url}/v1/batches/{non_existent_batch_id}"
    headers = {
        "Accept": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        assert response.status_code == 404, f"Expected 404 Not Found, got {response.status_code}"
        resp_json = response.json()
        assert isinstance(resp_json, dict), "Response JSON should be a dict"
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

test_get_v1_batches_batchid_status_notfound()