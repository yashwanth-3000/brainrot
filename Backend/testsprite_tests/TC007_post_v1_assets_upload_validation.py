import requests

BASE_URL = "http://localhost:8000"


def test_post_v1_assets_upload_validation():
    url = f"{BASE_URL}/v1/assets/upload"
    timeout = 30

    # (1) File but no kind → 422
    files = {'file': ('test.mp4', b'fake-video-content', 'video/mp4')}
    response1 = requests.post(url, files=files, timeout=timeout)
    assert response1.status_code == 422, f"Expected 422 but got {response1.status_code} for file without kind"

    # (2) Kind but no file → 422
    data = {'kind': 'gameplay'}
    response2 = requests.post(url, data=data, timeout=timeout)
    assert response2.status_code == 422, f"Expected 422 but got {response2.status_code} for kind without file"

    # (3) Invalid kind value → 422
    files = {'file': ('test.mp4', b'fake-video-content', 'video/mp4')}
    data = {'kind': 'invalidkind'}
    response3 = requests.post(url, files=files, data=data, timeout=timeout)
    assert response3.status_code == 422, f"Expected 422 but got {response3.status_code} for invalid kind value"


test_post_v1_assets_upload_validation()