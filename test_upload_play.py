import requests

# Đường dẫn file WAV để upload
audio_path = 'test_files/test_440hz.wav'

# URL backend
BASE_URL = 'http://localhost:5000'

# Đọc cookie từ file
with open('cookies.txt', 'r') as f:
    cookies = {}
    for line in f:
        if not line.startswith('#') and '\t' in line:
            parts = line.strip().split('\t')
            if len(parts) >= 7:
                cookies[parts[5]] = parts[6]

# Upload file WAV
def upload_audio():
    with open(audio_path, 'rb') as f:
        files = {'file': (audio_path, f, 'audio/wav')}
        resp = requests.post(f'{BASE_URL}/audio/upload', files=files, cookies=cookies)
        print('Upload response:', resp.status_code, resp.text)
        return resp.json() if resp.status_code == 200 else None

if __name__ == '__main__':
    upload_audio()
