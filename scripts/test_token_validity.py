from FinMind.data import DataLoader
import json
from pathlib import Path

# Load config to get token
config_path = Path("config/api_keys.json")
with open(config_path, "r") as f:
    config = json.load(f)
token = config.get("finmind", {}).get("token", "")

print(f"Testing token: {token[:5]}...{token[-5:]}")
dl = DataLoader()
try:
    dl.login_by_token(api_token=token)
    print("Login call succeeded (verified locally).")
    
    print("Fetching stock_info with token...")
    df = dl.taiwan_stock_info()
    print(f"Success! Retrieved {len(df)} stocks.")
    
    print("\nFetching market_value with token for 2330...")
    df = dl.taiwan_stock_market_value(stock_id='2330', start_date='2024-01-01', end_date='2024-01-05')
    print(f"Market value result:\n{df}")
except Exception as e:
    print(f"Failed: {e}")
