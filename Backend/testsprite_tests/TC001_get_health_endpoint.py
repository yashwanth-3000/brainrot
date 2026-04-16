import requests

def test_get_health_endpoint():
    url = "http://localhost:8000/health"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        json_data = response.json()
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        assert isinstance(json_data, dict), "Response is not a JSON object"
        assert 'status' in json_data, "'status' key not in response JSON"
        assert json_data['status'] == 'ok', f"Expected status 'ok', got {json_data['status']}"
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"
    except ValueError:
        assert False, "Response is not valid JSON"

test_get_health_endpoint()