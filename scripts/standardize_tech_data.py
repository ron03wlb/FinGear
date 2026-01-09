
import pandas as pd
from pathlib import Path
import tqdm
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parquet_manager import ParquetManager

def standardize_history():
    data_manager = ParquetManager(base_path='data')
    history_path = data_manager.history_path
    
    if not history_path.exists():
        print("History directory not found.")
        return

    # Define standard column mapping
    # We want: open, high, low, close, volume, amount, date, symbol/stock_id
    column_mapping = {
        'Trading_Volume': 'volume',
        'max': 'high',
        'min': 'low',
        'stock_id': 'symbol',
        'Trading_money': 'amount'
    }

    symbol_dirs = list(history_path.glob('symbol=*'))
    print(f"Standardizing {len(symbol_dirs)} history files...")

    for symbol_dir in tqdm.tqdm(symbol_dirs):
        data_file = symbol_dir / 'data.parquet'
        if not data_file.exists():
            continue
            
        try:
            df = pd.read_parquet(data_file)
            
            # Rename columns if they exist
            cols_to_rename = {k: v for k, v in column_mapping.items() if k in df.columns}
            if cols_to_rename:
                df = df.rename(columns=cols_to_rename)
            
            # Save back
            df.to_parquet(data_file)
        except Exception as e:
            print(f"Error standardizing {symbol_dir.name}: {e}")

if __name__ == "__main__":
    standardize_history()
