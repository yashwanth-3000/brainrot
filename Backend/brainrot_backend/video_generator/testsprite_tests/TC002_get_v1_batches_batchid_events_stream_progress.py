import requests
import sseclient
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_get_v1_batches_batchid_events_stream_progress():
    # Step 1: Create a new batch with valid source_url for test
    create_batch_url = f"{BASE_URL}/v1/batches"
    payload = {
        "source_url": "https://example.com/sample-article",
        "count": 5
    }
    headers = {
        "Content-Type": "application/json"
    }

    batch_id = None
    try:
        create_resp = requests.post(create_batch_url, json=payload, headers=headers, timeout=TIMEOUT)
        assert create_resp.status_code == 200, f"Batch creation failed, status code: {create_resp.status_code}"
        create_data = create_resp.json()
        assert "batch_id" in create_data, "batch_id missing in create batch response"
        batch_id = create_data["batch_id"]

        # Step 2: Connect to SSE stream for batch progress events
        sse_url = f"{BASE_URL}/v1/batches/{batch_id}/events"
        sse_headers = {
            "Accept": "text/event-stream"
        }
        with requests.get(sse_url, headers=sse_headers, stream=True, timeout=TIMEOUT) as resp:
            assert resp.status_code == 200, f"SSE stream request failed with status code {resp.status_code}"
            client = sseclient.SSEClient(resp)
            received_events = set()
            expected_events = {"ingest", "scripts_ready", "render", "upload", "done"}
            start_time = time.time()

            for event in client.events():
                # Each event data should be JSON string with at least a "stage" key
                try:
                    event_data = event.data
                    if event_data == "":  # keep alive event or empty, skip
                        continue
                    event_json = None
                    try:
                        event_json = event.data and requests.models.json.loads(event.data)
                    except Exception:
                        # fallback for some servers not sending JSON in event.data
                        event_json = None

                    if event_json and "stage" in event_json:
                        stage = event_json["stage"]
                        if stage in expected_events:
                            received_events.add(stage)
                    else:
                        # alternatively parse stage from raw data (string)
                        if any(stage in event.data for stage in expected_events):
                            for stage in expected_events:
                                if stage in event.data:
                                    received_events.add(stage)
                except Exception:
                    # just continue reading events on parse errors, but no crash
                    continue

                if received_events == expected_events:
                    break

                # Timeout after 25 seconds of streaming to avoid infinite wait
                if time.time() - start_time > 25:
                    break

            missing = expected_events - received_events
            assert not missing, f"Missing expected SSE events: {missing}"

    finally:
        # Cleanup: delete the created batch if possible
        if batch_id:
            try:
                delete_url = f"{BASE_URL}/v1/batches/{batch_id}"
                requests.delete(delete_url, timeout=TIMEOUT)
            except Exception:
                pass

test_get_v1_batches_batchid_events_stream_progress()