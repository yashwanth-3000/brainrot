import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_chats_create_and_get_chats_authentication():
    chat_id = None
    valid_token = "Bearer valid_test_token_example"  # Replace with a valid token if available
    invalid_token = "Bearer invalidtoken12345"
    headers_json = {"Content-Type": "application/json"}

    # Step 1: Create a chat (no auth needed or optional auth assumed)
    create_payload = {
        "title": "Test Chat for Authentication",
        "source_metadata": {"info": "test metadata"}
    }

    try:
        res_create = requests.post(
            f"{BASE_URL}/v1/chats", json=create_payload, headers=headers_json, timeout=TIMEOUT
        )
        assert res_create.status_code == 200 or res_create.status_code == 201, f"Unexpected status code on chat create: {res_create.status_code}"
        create_data = res_create.json()
        # Expect "chat_id" in create response as per PRD
        assert "chat_id" in create_data and create_data["chat_id"], "chat_id missing in create response"
        chat_id = create_data["chat_id"]

        # Step 2: GET /v1/chats with valid bearer token - expect scoped to user chats (including the created chat)
        headers_auth_valid = {"Authorization": valid_token}
        res_get_auth = requests.get(f"{BASE_URL}/v1/chats", headers=headers_auth_valid, timeout=TIMEOUT)
        assert res_get_auth.status_code == 200, f"Expected 200 for GET /v1/chats with valid token, got {res_get_auth.status_code}"
        data_auth = res_get_auth.json()
        assert isinstance(data_auth, list), "Expected list of chats"
        matching_chats = [c for c in data_auth if c.get("chat_id") == chat_id]
        assert len(matching_chats) > 0, "Created chat not found in authenticated user's chat list"

        # Step 3: GET /v1/chats without bearer token - expect general library chats (guest scope)
        res_get_guest = requests.get(f"{BASE_URL}/v1/chats", timeout=TIMEOUT)
        assert res_get_guest.status_code == 200, f"Expected 200 for GET /v1/chats without token, got {res_get_guest.status_code}"
        data_guest = res_get_guest.json()
        assert isinstance(data_guest, list), "Expected list of chats for guest"

        # Step 4: GET /v1/chats with invalid bearer token - expect 401 unauthorized
        headers_auth_invalid = {"Authorization": invalid_token}
        res_get_invalid = requests.get(f"{BASE_URL}/v1/chats", headers=headers_auth_invalid, timeout=TIMEOUT)
        assert res_get_invalid.status_code == 401, f"Expected 401 for GET /v1/chats with invalid token, got {res_get_invalid.status_code}"

    finally:
        if chat_id:
            try:
                requests.delete(f"{BASE_URL}/v1/chats/{chat_id}", headers=headers_json, timeout=TIMEOUT)
            except Exception:
                pass

test_post_v1_chats_create_and_get_chats_authentication()
