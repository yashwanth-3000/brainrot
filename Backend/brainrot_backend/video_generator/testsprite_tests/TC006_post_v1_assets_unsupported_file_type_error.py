import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_assets_unsupported_file_type_error():
    url = f"{BASE_URL}/v1/assets"

    # Prepare a dummy unsupported file type (e.g., .txt)
    files = {
        'file': ('testfile.txt', b'This is a test text content.', 'text/plain'),
    }
    # Metadata payload if needed - assuming 'kind' or other fields are optional or checked server-side
    data = {
        # No specific metadata required from PRD for error case
    }

    try:
        response = requests.post(url, files=files, data=data, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    # Check if status code is 400 or 422 as per error expectation
    assert response.status_code in (400, 422), \
        f"Expected status code 400 or 422, got {response.status_code} with body: {response.text}"

test_post_v1_assets_unsupported_file_type_error()