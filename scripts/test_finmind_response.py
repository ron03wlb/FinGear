
import requests
import json
from pathlib import Path

def test_finmind():
    config_path = Path('config/api_keys.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    token = config['finmind']['token']
    
    # Try a simple request using requests directly to see the raw response
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockFinancialStatements",
        "data_id": "2330",
        "start_date": "2024-01-01",
        "token": token
    }
    
    response = requests.get(url, params=params)
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print("Response JSON keys:", data.keys())
        if "msg" in data:
            print("Message:", data["msg"])
        if "data" in data:
            print("Data length:", len(data["data"]))
        else:
            print("Full response:", data)
    except Exception as e:
        print("Failed to parse JSON:", e)
        print("Raw content:", response.text[:500])

if __name__ == "__main__":
    test_finmind()
