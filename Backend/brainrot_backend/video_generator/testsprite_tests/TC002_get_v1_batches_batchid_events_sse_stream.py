import requests
import uuid
import time

BASE_URL = "http://localhost:8000"


def test_get_v1_batches_batchid_events_sse_stream():
    batch_id = None
    create_url = f"{BASE_URL}/v1/batches"
    create_data = {'source_url': 'https://example.com', 'count': '5'}
    headers_sse = {'Accept': 'text/event-stream'}

    # Step 1: Create a batch via POST /v1/batches with multipart/form-data
    try:
        create_resp = requests.post(create_url, data=create_data, timeout=30)
        assert create_resp.status_code == 200, f"Expected 200 but got {create_resp.status_code}"
        create_json = create_resp.json()
        assert 'batch' in create_json and 'id' in create_json['batch'], "Response JSON missing batch id"
        batch_id = create_json['batch']['id']
        # Validate batch_id is a valid UUID string
        uuid_obj = uuid.UUID(batch_id)

        # Step 2: Connect to SSE stream GET /v1/batches/{batch_id}/events
        events_url = f"{BASE_URL}/v1/batches/{batch_id}/events"
        with requests.get(events_url, headers=headers_sse, stream=True, timeout=10) as response:
            assert response.status_code == 200, f"SSE connect failed: {response.status_code}"
            content_type = response.headers.get('Content-Type', '')
            assert 'text/event-stream' in content_type.lower(), f"Unexpected Content-Type: {content_type}"

            # Step 3: Parse SSE manually by iterating response.iter_lines()
            # Read a few events within 10 seconds timeout then close
            start_time = time.time()
            event_count = 0
            max_events = 5
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    line = line.strip()
                    if line.startswith('data:'):
                        data_str = line[5:].strip()
                        # Basic assertion that data is present and non-empty
                        assert data_str, "Empty data field in SSE event"
                        event_count += 1
                # Break after reading max_events or timeout ~10 seconds
                if event_count >= max_events or (time.time() - start_time) > 10:
                    break

            assert event_count > 0, "No events received from SSE stream"

    finally:
        # Cleanup: attempt to delete batch if batch_id was created
        if batch_id:
            delete_url = f"{BASE_URL}/v1/batches/{batch_id}"
            try:
                requests.delete(delete_url, timeout=10)
            except Exception:
                pass


test_get_v1_batches_batchid_events_sse_stream()