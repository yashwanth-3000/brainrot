import requests
import time
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_get_v1_batches_sse_events():
    batch_id = None
    # Step 1: Create a batch
    try:
        post_url = f"{BASE_URL}/v1/batches"
        form_data = {'source_url': 'https://example.com', 'count': '5'}
        post_resp = requests.post(post_url, data=form_data, timeout=TIMEOUT)
        assert post_resp.status_code == 200, f"Expected 200, got {post_resp.status_code}"
        post_json = post_resp.json()
        assert 'batch' in post_json, "Response JSON missing 'batch' key"
        assert 'id' in post_json['batch'], "'id' missing in batch"
        batch_id = post_json['batch']['id']
        # Validate batch_id format is UUID
        try:
            uuid_obj = uuid.UUID(batch_id)
            assert str(uuid_obj) == batch_id
        except Exception:
            assert False, f"batch_id is not a valid UUID: {batch_id}"

        # Step 2: GET /v1/batches/{batch_id}/events with SSE headers and streaming
        sse_url = f"{BASE_URL}/v1/batches/{batch_id}/events"
        headers = {'Accept': 'text/event-stream'}
        with requests.get(sse_url, headers=headers, stream=True, timeout=TIMEOUT) as resp:
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            content_type = resp.headers.get('content-type', '')
            assert 'text/event-stream' in content_type.lower(), f"Content-Type does not contain 'text/event-stream': {content_type}"

            # Read events up to 10 seconds
            start_time = time.time()
            parsed_events = []
            for line in resp.iter_lines(decode_unicode=True):
                if line:
                    # lines beginning with "data:" contain event data in SSE protocol
                    if line.startswith('data:'):
                        data = line[5:].strip()
                        parsed_events.append(data)
                if time.time() - start_time > 10:
                    break
    finally:
        # Cleanup: delete created batch if possible (not defined in PRD, so skipping)
        # No delete endpoint specified for batch, so no operation
        pass

test_get_v1_batches_sse_events()