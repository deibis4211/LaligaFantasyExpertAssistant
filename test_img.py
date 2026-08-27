import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://biwenger.as.com/'
}

url = "https://cf.biwenger.com/api/v2/players/17731/image"
try:
    r = requests.get(url, headers=headers, timeout=5)
    print(f"{url} -> {r.status_code}")
    print("Redirect history:", r.history)
    print("Final URL:", r.url)
except Exception as e:
    print(f"{url} -> Error: {e}")
