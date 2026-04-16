import requests
import uuid

BASE_URL = "http://localhost:8000"

def test_post_v1_batches_create_batch():
    url = f"{BASE_URL}/v1/batches"
    data = {'source_url': 'https://example.com', 'count': '5'}
    timeout = 30
    try:
        response = requests.post(url, data=data, timeout=timeout)
        response.raise_for_status()
        assert response.status_code == 200
        json_resp = response.json()
        assert 'batch' in json_resp
        assert 'items' in json_resp
        batch = json_resp['batch']
        batch_id = batch.get('id')
        assert batch_id is not None, "batch id missing"
        # Validate batch_id is a valid UUID string
        try:
            uuid_obj = uuid.UUID(batch_id)
            assert str(uuid_obj) == batch_id
        except Exception:
            assert False, "batch id is not a valid UUID string"
        # items must be a list
        assert isinstance(json_resp['items'], list)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

test_post_v1_batches_create_batch()