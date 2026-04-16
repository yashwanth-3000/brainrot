import requests

BASE_URL = "http://localhost:8000"


def test_post_v1_agents_bootstrap():
    url = f"{BASE_URL}/v1/agents/bootstrap"
    try:
        response = requests.post(url, timeout=30)
        response.raise_for_status()
        assert response.status_code == 200

        json_data = response.json()
        # Verify keys
        assert 'agents' in json_data
        assert 'tool_ids' in json_data

        # Verify agents and tool_ids are lists
        assert isinstance(json_data['agents'], list)
        assert isinstance(json_data['tool_ids'], list)

        # Each agent must have 'id', 'role', 'name', 'agent_id'
        for agent in json_data['agents']:
            assert isinstance(agent, dict)
            for key in ['id', 'role', 'name', 'agent_id']:
                assert key in agent
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"


test_post_v1_agents_bootstrap()