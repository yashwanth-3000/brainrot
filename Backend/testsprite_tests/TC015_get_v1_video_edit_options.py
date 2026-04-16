import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_get_v1_video_edit_options():
    url = f"{BASE_URL}/v1/video-edit/options"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        data = response.json()
        assert "gameplay_assets" in data, "'gameplay_assets' not in response"
        assert isinstance(data["gameplay_assets"], list), "'gameplay_assets' is not a list"
        assert "subtitle_presets" in data, "'subtitle_presets' not in response"
        assert isinstance(data["subtitle_presets"], list), "'subtitle_presets' is not a list"
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

test_get_v1_video_edit_options()