import requests
import uuid

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_assets_upload():
    url = f"{BASE_URL}/v1/assets/upload"
    files = {
        'file': ('test.mp4', b'fake-video-content', 'video/mp4')
    }
    data = {
        'kind': 'gameplay',
        'tags': 'test',
        'metadata_json': '{}'
    }

    try:
        response = requests.post(url, files=files, data=data, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected status 200 but got {response.status_code}"
        json_resp = response.json()
        assert 'asset' in json_resp, "'asset' key not in response JSON"
        asset = json_resp['asset']
        assert 'id' in asset, "'id' not found in asset"
        # Validate UUID format
        asset_id = asset['id']
        uuid.UUID(asset_id)
        assert 'kind' in asset and asset['kind'] == 'gameplay', "Asset kind is not 'gameplay'"
    except requests.RequestException as e:
        assert False, f"Request failed: {str(e)}"
    except ValueError as ve:
        assert False, f"Invalid UUID returned: {str(ve)}"

test_post_v1_assets_upload()