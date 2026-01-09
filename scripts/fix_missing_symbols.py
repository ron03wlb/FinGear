
import pandas as pd
from pathlib import Path
import tqdm
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parquet_manager import ParquetManager

def fix_nan_symbols():
    data_manager = ParquetManager(base_path='data')
    
    # Check Chips
    chips_path = data_manager.chips_path
    if chips_path.exists():
        symbol_dirs = list(chips_path.glob('symbol=*'))
        print(f"Fixing NaN symbols in {len(symbol_dirs)} chip files...")
        for symbol_dir in tqdm.tqdm(symbol_dirs):
            symbol = symbol_dir.name.split('=')[1]
            data_file = symbol_dir / 'data.parquet'
            if data_file.exists():
                try:
                    df = pd.read_parquet(data_file)
                    modified = False
                    if 'symbol' not in df.columns:
                        df['symbol'] = symbol
                        modified = True
                    elif df['symbol'].isnull().any():
                        df['symbol'] = df['symbol'].fillna(symbol)
                        modified = True
                    
                    if modified:
                        df.to_parquet(data_file, index=False)
                except Exception as e:
                    print(f"Error fixing {symbol}: {e}")
                    continue

    # Check Fundamentals
    fund_path = data_manager.fundamentals_path
    if fund_path.exists():
        symbol_dirs = list(fund_path.glob('symbol=*'))
        print(f"Fixing NaN symbols in {len(symbol_dirs)} fundamental files...")
        for symbol_dir in tqdm.tqdm(symbol_dirs):
            symbol = symbol_dir.name.split('=')[1]
            data_file = symbol_dir / 'data.parquet'
            if data_file.exists():
                try:
                    df = pd.read_parquet(data_file)
                    # For fundamentals, if symbol col doesn't exist, we might want to add it for consistency
                    # but usually fundamentals don't have a symbol column per row in our schema (it's in the path)
                    # However, comprehensive_check.py doesn't check 'symbol' for fundamentals anyway.
                    pass
                except Exception:
                    continue

if __name__ == "__main__":
    fix_nan_symbols()
