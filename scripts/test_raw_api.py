import requests
import json
from pathlib import Path

# Load config to get token
config_path = Path("config/api_keys.json")
with open(config_path, "r") as f:
    config = json.load(f)
token = config.get("finmind", {}).get("token", "")

url = "https://api.finmindtrade.com/api/v4/data"

params = {
    "dataset": "TaiwanStockMarketValue",
    "data_id": "2330",
    "start_date": "2024-01-01",
    "end_date": "2024-01-05",
    "token": token
}

print(f"Requesting: {url} with params {params}")
response = requests.get(url, params=params)
print(f"Status Code: {response.status_code}")
try:
    data = response.json()
    print(f"Response JSON: {json.dumps(data, indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"Failed to parse JSON: {e}")
    print(f"Raw content: {response.text}")
