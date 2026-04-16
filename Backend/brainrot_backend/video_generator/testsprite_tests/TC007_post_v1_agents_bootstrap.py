import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_agents_bootstrap():
    url = f"{BASE_URL}/v1/agents/bootstrap"
    try:
        response = requests.post(url, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        json_data = response.json()
        assert isinstance(json_data, dict), "Response JSON is not a dictionary"
        assert 'agents' in json_data, "'agents' key missing in response"
        assert 'tool_ids' in json_data, "'tool_ids' key missing in response"
        assert isinstance(json_data['agents'], list), "'agents' is not a list"
        assert isinstance(json_data['tool_ids'], list), "'tool_ids' is not a list"
        for agent in json_data['agents']:
            assert isinstance(agent, dict), "Each agent should be a dict"
            for field in ['id', 'role', 'name', 'agent_id']:
                assert field in agent, f"Agent missing field '{field}'"
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

test_post_v1_agents_bootstrap()