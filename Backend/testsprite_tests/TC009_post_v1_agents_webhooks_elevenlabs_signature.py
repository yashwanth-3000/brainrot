import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_agents_webhooks_elevenlabs_signature():
    url = f"{BASE_URL}/v1/agents/webhooks/elevenlabs"
    json_body = {"test": "data"}

    # Case 1: No signature header → 400 with expected detail
    try:
        response = requests.post(url, json=json_body, timeout=TIMEOUT)
    except Exception as e:
        assert False, f"Request to {url} failed: {e}"
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    try:
        resp_json = response.json()
    except Exception:
        assert False, "Response is not valid JSON"
    detail = resp_json.get("detail") or resp_json.get("message") or ""
    assert "Missing ElevenLabs webhook signature header." in detail, f"Unexpected detail message: {detail}"

    # Case 2: Fake signature header with JSON body → 400
    headers = {
        "elevenlabs-signature": "fake"
    }
    try:
        response = requests.post(url, json=json_body, headers=headers, timeout=TIMEOUT)
    except Exception as e:
        assert False, f"Request to {url} failed: {e}"
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"

test_post_v1_agents_webhooks_elevenlabs_signature()