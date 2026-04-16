import requests
import io

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_v1_assets_upload_gameplay_music_font():
    url = f"{BASE_URL}/v1/assets"
    headers = {}  # No special auth headers provided, guest scope assumed
    
    gameplay_clip_content = b'\x00\x00\x00\x18ftypmp42'  # minimal mp4 header bytes
    music_file_content = b'ID3\x04\x00\x00\x00\x00\x00\x21'  # minimal mp3 header bytes
    font_file_content = b'\x00\x01\x00\x00\x00\x0c\x00\x80\x00\x03\x00\x50'  # minimal ttf header bytes
    
    def upload_asset(file_content, filename, metadata_dict, expected_kind, content_type):
        files = {
            'file': (filename, io.BytesIO(file_content), content_type),
        }
        data = metadata_dict  # metadata sent as form fields, not JSON string
        try:
            resp = requests.post(url, files=files, data=data, timeout=TIMEOUT, headers=headers)
        except requests.RequestException as e:
            assert False, f"Request failed: {e}"
        assert resp.status_code == 200, f"Unexpected status code {resp.status_code}, body: {resp.text}"
        try:
            data_resp = resp.json()
        except Exception as e:
            assert False, f"Response is not JSON: {e}"
        
        assert "id" in data_resp and isinstance(data_resp["id"], str) and data_resp["id"], "Missing or invalid 'id' in response"
        assert data_resp.get("kind") == expected_kind, f"Expected kind '{expected_kind}', got '{data_resp.get('kind')}'"
        
        return data_resp["id"]
    
    created_ids = []
    try:
        gameplay_metadata = {"description":"Test gameplay clip upload"}
        gameplay_id = upload_asset(gameplay_clip_content, "gameplay_clip.mp4", gameplay_metadata, "GAMEPLAY", "video/mp4")
        created_ids.append(gameplay_id)
        
        music_metadata = {"description":"Test music upload"}
        music_id = upload_asset(music_file_content, "music_file.mp3", music_metadata, "MUSIC", "audio/mpeg")
        created_ids.append(music_id)
        
        font_metadata = {"description":"Test font upload"}
        font_id = upload_asset(font_file_content, "font_file.ttf", font_metadata, "FONT", "font/ttf")
        created_ids.append(font_id)
        
    finally:
        pass

test_post_v1_assets_upload_gameplay_music_font()
