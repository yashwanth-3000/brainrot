import requests
import uuid

def test_post_v1_batches_create_batch_with_form_data():
    base_url = "http://localhost:8000"
    url = f"{base_url}/v1/batches"
    form_data = {
        'source_url': 'https://example.com',
        'count': '5'
    }
    try:
        response = requests.post(url, data=form_data, timeout=30)
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        json_resp = response.json()
        assert 'batch' in json_resp, "'batch' key missing in response"
        batch = json_resp['batch']
        batch_id = batch.get('id', '')
        # Validate batch_id is a non-empty UUID string
        assert batch_id, "Batch id is empty"
        try:
            uuid_obj = uuid.UUID(batch_id)
        except ValueError:
            assert False, f"Batch id is not a valid UUID string: {batch_id}"
        assert 'items' in json_resp, "'items' key missing in response"
        items = json_resp['items']
        assert isinstance(items, list), f"'items' is not a list, got {type(items)}"
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

test_post_v1_batches_create_batch_with_form_data()