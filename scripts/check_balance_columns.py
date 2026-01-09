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

print("Fetching balance sheet for 2330...")
try:
    df = dl.taiwan_stock_balance_sheet(
        stock_id='2330',
        start_date='2024-01-01',
        end_date='2024-12-31'
    )
    if not df.empty:
        types = df['type'].unique().tolist()
        print(f"Available types: {types}")
        # Look for something like 'Ordinary share' or 'Capital stock'
        capital_types = [t for t in types if 'Stock' in t or 'Capital' in t or '股本' in t or 'OrdinaryShare' in t]
        print(f"Potential capital types: {capital_types}")
        
        # If we find it, show the value
        for ct in capital_types:
            val = df[df['type'] == ct].iloc[-1]['value']
            print(f"Value for {ct}: {val}")
    else:
        print("Empty balance sheet.")
except Exception as e:
    print(f"Failed: {e}")
