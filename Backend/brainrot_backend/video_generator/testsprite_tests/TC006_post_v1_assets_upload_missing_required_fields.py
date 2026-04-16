import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_assets_upload_missing_required_fields():
    url = f"{BASE_URL}/v1/assets/upload"
    
    # Test case 1: file but no 'kind' field
    files = {'file': ('test.mp4', b'content', 'video/mp4')}
    data = {}
    response1 = requests.post(url, files=files, data=data, timeout=TIMEOUT)
    assert response1.status_code == 422, f"Expected 422 for missing 'kind', got {response1.status_code}"
    
    # Test case 2: 'kind' but no file
    data = {'kind': 'gameplay'}
    response2 = requests.post(url, data=data, timeout=TIMEOUT)
    assert response2.status_code == 422, f"Expected 422 for missing file, got {response2.status_code}"
    
    # Test case 3: invalid kind value
    files = {'file': ('t.mp4', b'x', 'video/mp4')}
    data = {'kind': 'invalid_kind'}
    response3 = requests.post(url, files=files, data=data, timeout=TIMEOUT)
    assert response3.status_code == 422, f"Expected 422 for invalid kind, got {response3.status_code}"

test_post_v1_assets_upload_missing_required_fields()