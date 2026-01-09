from FinMind.data import DataLoader
import pandas as pd

dl = DataLoader()
# No login

print("Testing taiwan_stock_info (should be public)...")
try:
    df = dl.taiwan_stock_info()
    print(f"Success! Retrieved {len(df)} stocks.")
except Exception as e:
    print(f"Failed: {e}")

print("\nTesting taiwan_stock_daily for 2330 (limited history)...")
try:
    df = dl.taiwan_stock_daily(stock_id='2330', start_date='2024-01-01', end_date='2024-01-05')
    print(f"Result:\n{df}")
except Exception as e:
    print(f"Failed: {e}")
