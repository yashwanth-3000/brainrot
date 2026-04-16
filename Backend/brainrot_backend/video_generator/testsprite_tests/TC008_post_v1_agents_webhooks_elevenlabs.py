import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_agents_webhooks_elevenlabs():
    url = f"{BASE_URL}/v1/agents/webhooks/elevenlabs"

    # Test case 1: Missing signature header should return 400 with specific detail
    response_no_header = requests.post(url, json={}, timeout=TIMEOUT)
    assert response_no_header.status_code == 400
    json_resp_no_header = response_no_header.json()
    assert "detail" in json_resp_no_header
    assert json_resp_no_header["detail"] == "Missing ElevenLabs webhook signature header."

    # Test case 2: Fake signature header and JSON body should return 400 (signature failure)
    headers_fake_sig = {"elevenlabs-signature": "fake_sig"}
    payload = {"some": "data"}
    response_fake_sig = requests.post(url, headers=headers_fake_sig, json=payload, timeout=TIMEOUT)
    assert response_fake_sig.status_code == 400

test_post_v1_agents_webhooks_elevenlabs()