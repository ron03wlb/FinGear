import requests
import json
import pandas as pd
from datetime import datetime, timedelta

def get_twse_market_value(date_str: str):
    """
    Fetch market value info from TWSE MI_INDEX
    """
    # MI_INDEX has multiple tables. The one we want usually contains stock info.
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={date_str}&type=ALLBUT0999&response=json"
    print(f"Fetching from {url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            return None
        
        data = response.json()
        if data.get('stat') != 'OK':
            print(f"TWSE returned non-OK status for {date_str}: {data.get('stat')}")
            return None
            
        # The table with stock prices and outstanding shares is usually tables[8] or similar
        # We need to find the table where headers include '證券代號' and something about shares
        for i, table in enumerate(data.get('tables', [])):
            fields = table.get('fields', [])
            if '證券代號' in fields and '證券名稱' in fields:
                print(f"Found stock table at index {i}")
                df = pd.DataFrame(table.get('data', []), columns=fields)
                return df
                
        return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

# Try recent dates (excluding weekends)
test_date = "20251231" # Wednesday
df = get_twse_market_value(test_date)
if df is not None:
    print(f"Success! Columns: {df.columns.tolist()}")
    print("First 5 rows:")
    print(df.head())
    # Check if we can find market cap related columns
    # Usually it has '成交股數', '成交金額', '開盤價', '最高價', '最低價', '收盤價', etc.
    # It might NOT have market cap or shares outstanding directly in MI_INDEX.
else:
    print("Failed to get data.")
