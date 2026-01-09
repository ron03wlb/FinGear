
import sys
from pathlib import Path
import pandas as pd
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parquet_manager import ParquetManager

def calculate_column_coverage():
    data_manager = ParquetManager(base_path='data')
    fundamentals_path = data_manager.fundamentals_path
    
    if not fundamentals_path.exists():
        print("Fundamentals directory not found.")
        return

    all_cols = set()
    stock_data = {}
    
    stocks = []
    for symbol_dir in fundamentals_path.iterdir():
        if symbol_dir.is_dir() and symbol_dir.name.startswith('symbol='):
            symbol = symbol_dir.name.split('=')[1]
            try:
                df = data_manager.read_fundamental_data(symbol)
                if df is not None and not df.empty:
                    stocks.append(symbol)
                    all_cols.update(df.columns)
                    stock_data[symbol] = df
            except Exception:
                continue
    
    total_stocks = len(stocks)
    print(f"Analyzing {total_stocks} stocks...")
    
    coverage = {}
    for col in all_cols:
        count = 0
        for symbol in stocks:
            df = stock_data[symbol]
            if col in df.columns and not df[col].isnull().all():
                # Check if the latest record has data
                if not pd.isnull(df[col].iloc[-1]):
                    count += 1
        
        coverage[col] = (count / total_stocks) * 100
    
    print("\nIndicator Collection Rates (latest record):")
    print("-" * 40)
    for col, rate in sorted(coverage.items(), key=lambda x: x[1]):
        print(f"{col:<25}: {rate:>6.1f}%")

if __name__ == "__main__":
    calculate_column_coverage()
