from FinMind.data import DataLoader
import json
from pathlib import Path

# Load config to get token
config_path = Path("config/api_keys.json")
with open(config_path, "r") as f:
    config = json.load(f)
token = config.get("finmind", {}).get("token", "")

dl = DataLoader()
dl.login_by_token(api_token=token)

print("Fetching financial statement for 2330...")
try:
    df = dl.taiwan_stock_financial_statement(
        stock_id='2330',
        start_date='2024-01-01',
        end_date='2024-12-31'
    )
    if not df.empty:
        types = df['type'].unique().tolist()
        print(f"Available types: {types}")
        # Look for something like 'Common stock' or 'Share capital'
        capital_types = [t for t in types if 'Stock' in t or 'Capital' in t or '股本' in t]
        print(f"Potential capital types: {capital_types}")
    else:
        print("Empty financial statement.")
except Exception as e:
    print(f"Failed: {e}")
