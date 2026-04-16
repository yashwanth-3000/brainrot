import requests
import json

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
HEADERS = {
    "Content-Type": "application/json"
}


def test_post_v1_batches_create_batch_job():
    url = f"{BASE_URL}/v1/batches"
    payload = {
        "source_url": "https://example.com/sample-article-to-video",
        "count": 5
    }
    response = None
    batch_id = None
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=TIMEOUT)
        assert response.status_code == 200 or response.status_code == 201, f"Unexpected status code: {response.status_code}"
        body = response.json()
        assert "batch_id" in body, "Response missing 'batch_id'"
        assert "items" in body, "Response missing 'items'"
        assert isinstance(body["items"], list), "'items' is not a list"
        batch_id = body["batch_id"]
        # Additional sanity check: items list can be empty or have initial items, so just verify type
        assert batch_id and isinstance(batch_id, str) and len(batch_id) > 0, "'batch_id' invalid"
    finally:
        # Cleanup: try delete the batch if batch_id created (assuming DELETE supported)
        if batch_id:
            try:
                delete_response = requests.delete(f"{BASE_URL}/v1/batches/{batch_id}", timeout=TIMEOUT)
                # ignore response code for cleanup
            except Exception:
                pass


test_post_v1_batches_create_batch_job()
