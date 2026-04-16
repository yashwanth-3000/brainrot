import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_assets_upload_file():
    url = f"{BASE_URL}/v1/assets/upload"
    files = {
        'file': ('test.mp4', b'fake-content', 'video/mp4')
    }
    data = {
        'kind': 'gameplay',
        'tags': 'test',
        'metadata_json': '{}'
    }
    response = None
    asset_id = None
    try:
        response = requests.post(url, files=files, data=data, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        json_data = response.json()
        assert 'asset' in json_data, "'asset' key missing in response"
        asset = json_data['asset']
        assert 'id' in asset and asset['id'], "'id' missing or empty in asset"
        assert asset.get('kind') == data['kind'], f"Expected kind '{data['kind']}', got '{asset.get('kind')}'"
        asset_id = asset['id']
    finally:
        if asset_id:
            # Attempt to delete the uploaded asset to clean up (if such endpoint exists)
            # This is speculative as PRD does not mention delete asset endpoint.
            # We'll attempt DELETE /v1/assets/{asset_id} if it exists.
            delete_url = f"{BASE_URL}/v1/assets/{asset_id}"
            try:
                del_resp = requests.delete(delete_url, timeout=TIMEOUT)
                # No assertion on delete response as endpoint is unknown
            except Exception:
                pass

test_post_v1_assets_upload_file()