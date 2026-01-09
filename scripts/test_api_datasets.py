from FinMind.data import DataLoader
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path

# Load config to get token
config_path = Path("config/api_keys.json")
with open(config_path, "r") as f:
    config = json.load(f)
token = config.get("finmind", {}).get("token", "")

dl = DataLoader()
dl.login_by_token(api_token=token)

end_date = datetime.now()
start_date = end_date - timedelta(days=30)
start_str = start_date.strftime('%Y-%m-%d')
end_str = end_date.strftime('%Y-%m-%d')

datasets_to_test = [
    'TaiwanStockMarketValue',
    'TaiwanStockDaily',
    'TaiwanStockFinancialStatement'
]

for ds in datasets_to_test:
    print(f"\n--- Testing Dataset: {ds} ---")
    try:
        df = dl.get_data(
            dataset=ds,
            data_id='2330',
            start_date=start_str,
            end_date=end_str
        )
        if df is not None:
            print(f"Success! Column names: {df.columns.tolist()}")
            print(f"First row: \n{df.head(1)}")
        else:
            print("Returned None")
    except Exception as e:
        print(f"Failed: {e}")
