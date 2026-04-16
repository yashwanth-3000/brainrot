import requests
import hmac
import hashlib
import json

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def post_v1_agents_webhook_elevenlabs_hmac_validation():
    url = f"{BASE_URL}/v1/agents/webhook/elevenlabs"
    secret_key = b"test_secret_key"  # This should match the server's expected secret for HMAC validation

    # Example valid payload (script bundle)
    payload = {
        "bundle_id": "test_bundle_123",
        "scripts": [
            {"script_id": "script1", "content": "Test script content 1"},
            {"script_id": "script2", "content": "Test script content 2"}
        ]
    }

    # Convert payload to JSON string for HMAC calculation
    payload_json = json.dumps(payload, separators=(',', ':'))

    # Calculate valid HMAC signature
    valid_hmac = hmac.new(secret_key, payload_json.encode('utf-8'), hashlib.sha256).hexdigest()

    headers_valid = {
        "Content-Type": "application/json",
        "X-ElevenLabs-HMAC": valid_hmac
    }

    # Make POST request with valid HMAC signature
    try:
        response_valid = requests.post(url, headers=headers_valid, data=payload_json, timeout=TIMEOUT)
        assert response_valid.status_code == 200, f"Expected 200 OK, got {response_valid.status_code}"
    except Exception as e:
        raise AssertionError(f"Valid HMAC request failed: {e}")

    # Invalid HMAC signature (change one char)
    invalid_hmac = valid_hmac[:-1] + ('0' if valid_hmac[-1] != '0' else '1')
    headers_invalid = {
        "Content-Type": "application/json",
        "X-ElevenLabs-HMAC": invalid_hmac
    }

    # Make POST request with invalid HMAC signature
    try:
        response_invalid = requests.post(url, headers=headers_invalid, data=payload_json, timeout=TIMEOUT)
        assert response_invalid.status_code == 401, f"Expected 401 Unauthorized, got {response_invalid.status_code}"
    except Exception as e:
        raise AssertionError(f"Invalid HMAC request failed: {e}")

post_v1_agents_webhook_elevenlabs_hmac_validation()