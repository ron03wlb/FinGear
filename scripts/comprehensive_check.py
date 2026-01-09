
import sys
from pathlib import Path
import pandas as pd
import glob
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parquet_manager import ParquetManager

def get_symbols_from_doc():
    stock_file = Path('docs/500_stocks.txt')
    symbols = []
    if stock_file.exists():
        with open(stock_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split()
                    if parts and parts[0].isdigit() and len(parts[0]) == 4:
                        symbols.append(parts[0])
    return symbols

def check_coverage():
    data_manager = ParquetManager(base_path='data')
    target_symbols = get_symbols_from_doc()
    total_target = len(target_symbols)
    
    if total_target == 0:
        print("No target symbols found in docs/500_stocks.txt")
        return

    print(f"Target Universe: {total_target} stocks (from docs/500_stocks.txt)")
    
    results = {}

    # 1. Fundamental
    fundamental_cols = {}
    for symbol in target_symbols:
        try:
            df = data_manager.read_fundamental_data(symbol)
            if df is not None and not df.empty:
                for col in df.columns:
                    if col not in fundamental_cols: fundamental_cols[col] = 0
                    if not pd.isnull(df[col].iloc[-1]):
                        fundamental_cols[col] += 1
        except Exception:
            continue
    
    for col, count in fundamental_cols.items():
        results[f"Fundamental: {col}"] = (count / total_target) * 100

    # 2. Chips
    chip_cols = {}
    for symbol in target_symbols:
        try:
            df = data_manager.read_chip_data(symbol)
            if df is not None and not df.empty:
                for col in df.columns:
                    if col not in chip_cols: chip_cols[col] = 0
                    if not pd.isnull(df[col].iloc[-1]):
                        chip_cols[col] += 1
        except Exception:
            continue
            
    for col, count in chip_cols.items():
        results[f"Chip: {col}"] = (count / total_target) * 100

    # 3. Shareholding
    share_cols = {}
    for symbol in target_symbols:
        try:
            path = Path(f'data/shareholding/symbol={symbol}/data.parquet')
            if path.exists():
                df = pd.read_parquet(path)
                if not df.empty:
                    for col in df.columns:
                        if col not in share_cols: share_cols[col] = 0
                        if not pd.isnull(df[col].iloc[-1]):
                            share_cols[col] += 1
        except Exception:
            continue
            
    for col, count in share_cols.items():
        results[f"Shareholding: {col}"] = (count / total_target) * 100

    # 4. Technical (History)
    tech_cols = {}
    for symbol in target_symbols:
        try:
            path = Path(f'data/history/symbol={symbol}/data.parquet')
            if path.exists():
                df = pd.read_parquet(path)
                if not df.empty:
                    for col in df.columns:
                        if col not in tech_cols: tech_cols[col] = 0
                        if not pd.isnull(df[col].iloc[-1]):
                            tech_cols[col] += 1
        except Exception:
            continue
            
    for col, count in tech_cols.items():
        results[f"Technical: {col}"] = (count / total_target) * 100

    print("\nIndicator Collection Rates (relative to 500_stocks.txt):")
    print("-" * 60)
    
    sorted_results = sorted(results.items(), key=lambda x: x[1])
    for indicator, rate in sorted_results:
        if rate < 100:
            status = "❌"
            print(f"{status} {indicator:<40}: {rate:>6.1f}%")
    
    print("\nIndicators with 100% coverage:")
    print("-" * 60)
    for indicator, rate in sorted_results:
        if rate == 100:
            status = "✅"
            print(f"{status} {indicator:<40}: {rate:>6.1f}%")

if __name__ == "__main__":
    check_coverage()
