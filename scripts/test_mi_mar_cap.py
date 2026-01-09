import requests
import pandas as pd

def get_twse_mi_mar_cap(date_str: str):
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_MAR_CAP?date={date_str}&response=json"
    print(f"Fetching from {url}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if data.get('stat') != 'OK':
            print(f"TWSE returned: {data.get('stat')}")
            return None
            
        for i, table in enumerate(data.get('tables', [])):
            fields = table.get('fields', [])
            if '證券代號' in fields and '市值(百萬元)' in fields:
                print(f"Found market cap table at index {i}")
                df = pd.DataFrame(table.get('data', []), columns=fields)
                return df
        return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

df = get_twse_mi_mar_cap("20251231")
if df is not None:
    print(f"Success! Columns: {df.columns.tolist()}")
    print("Top 10 by Market Cap (after cleaning):")
    # Clean up commas and convert to numeric
    df['市值(百萬元)'] = df['市值(百萬元)'].str.replace(',', '').astype(float)
    df = df.sort_values('市值(百萬元)', ascending=False)
    print(df.head(10))
else:
    print("Failed to get data.")
