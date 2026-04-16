import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
HEADERS_JSON = {"Content-Type": "application/json"}


def test_post_v1_agents_bootstrap_and_proxy():
    # Step 1: POST /v1/agents/bootstrap to bootstrap ElevenLabs agents
    bootstrap_url = f"{BASE_URL}/v1/agents/bootstrap"
    try:
        bootstrap_resp = requests.post(bootstrap_url, timeout=TIMEOUT)
        bootstrap_resp.raise_for_status()
        bootstrap_data = bootstrap_resp.json()
        assert isinstance(bootstrap_data, dict)
        # Expecting agent IDs or similar keys in response
        assert "agent_ids" in bootstrap_data or "agents" in bootstrap_data
    except requests.RequestException as e:
        raise AssertionError(f"POST /v1/agents/bootstrap failed: {e}")

    # Prepare valid payload for POST /v1/agents/custom-llm/chat
    chat_url = f"{BASE_URL}/v1/agents/custom-llm/chat"
    chat_payload = {
        "model": "elevenlabs-llm",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, test chat"}
        ],
        "temperature": 0.7,
        "max_tokens": 50
    }

    try:
        chat_resp = requests.post(chat_url, json=chat_payload, headers=HEADERS_JSON, timeout=TIMEOUT)
        chat_resp.raise_for_status()
        chat_data = chat_resp.json()
        assert isinstance(chat_data, dict)
        # Typical chat completion keys check
        assert "choices" in chat_data
        assert isinstance(chat_data["choices"], list)
        assert len(chat_data["choices"]) > 0
        for choice in chat_data["choices"]:
            assert "message" in choice and "content" in choice["message"]
    except requests.RequestException as e:
        raise AssertionError(f"POST /v1/agents/custom-llm/chat failed: {e}")

    # Prepare valid payload for POST /v1/agents/custom-llm/responses
    responses_url = f"{BASE_URL}/v1/agents/custom-llm/responses"
    responses_payload = {
        "model": "elevenlabs-llm",
        "prompt": "Summarize the benefits of AI.",
        "max_tokens": 60,
        "temperature": 0.7
    }

    try:
        responses_resp = requests.post(responses_url, json=responses_payload, headers=HEADERS_JSON, timeout=TIMEOUT)
        responses_resp.raise_for_status()
        responses_data = responses_resp.json()
        assert isinstance(responses_data, dict)
        # Validate typical OpenAI proxy response structure
        assert "id" in responses_data or "choices" in responses_data
        if "choices" in responses_data:
            assert isinstance(responses_data["choices"], list)
            assert len(responses_data["choices"]) > 0
            for choice in responses_data["choices"]:
                assert "text" in choice or "message" in choice
    except requests.RequestException as e:
        raise AssertionError(f"POST /v1/agents/custom-llm/responses failed: {e}")


test_post_v1_agents_bootstrap_and_proxy()