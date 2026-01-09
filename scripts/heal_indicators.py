
import os
import sys
import logging
import pandas as pd
from pathlib import Path
from typing import List, Set, Dict
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.finmind_client import FinMindClient
from src.parquet_manager import ParquetManager
from scripts.collect_fundamental_data import load_api_config, calculate_date_range, merge_fundamental_data
from scripts.fix_missing_symbols import fix_nan_symbols
from scripts.standardize_tech_data import standardize_history as standardize_tech_files

def get_target_symbols() -> List[str]:
    """從 docs/500_stocks.txt 載入目標股票"""
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

def find_gaps(symbols: List[str], data_manager: ParquetManager) -> Dict[str, Set[str]]:
    """找出遺漏指標的股票"""
    gaps = {
        'net_income': set(),
        'operating_cash_flow': set(),
        'fundamental_file': set(),
        'chip_file': set(),
        'tech_file': set()
    }
    
    for symbol in symbols:
        # Fundamental gaps
        fund_p = Path(f'data/fundamentals/symbol={symbol}/data.parquet')
        if not fund_p.exists():
            gaps['fundamental_file'].add(symbol)
            gaps['net_income'].add(symbol)
            gaps['operating_cash_flow'].add(symbol)
        else:
            try:
                df = pd.read_parquet(fund_p)
                if df.empty:
                    gaps['fundamental_file'].add(symbol)
                    gaps['net_income'].add(symbol)
                    gaps['operating_cash_flow'].add(symbol)
                else:
                    latest = df.iloc[-1]
                    if 'net_income' not in df.columns or pd.isna(latest['net_income']):
                        gaps['net_income'].add(symbol)
                    if 'operating_cash_flow' not in df.columns or pd.isna(latest['operating_cash_flow']):
                        gaps['operating_cash_flow'].add(symbol)
            except Exception:
                gaps['fundamental_file'].add(symbol)
        
        # Chip gaps
        if not Path(f'data/chips/symbol={symbol}/data.parquet').exists():
            gaps['chip_file'].add(symbol)
            
        # Tech gaps
        if not Path(f'data/history/symbol={symbol}/data.parquet').exists():
            gaps['tech_file'].add(symbol)
            
    return gaps

def apply_local_fixes(symbols: List[str]):
    """套用本地數據修復（如金融股映射）"""
    print("Applying local data fixes...")
    for s in tqdm(symbols, desc="Healing locals"):
        p = Path(f'data/fundamentals/symbol={s}/data.parquet')
        if p.exists():
            try:
                df = pd.read_parquet(p)
                modified = False
                
                # 1. Gross Profit fallback (Banks)
                if 'gross_profit' not in df.columns:
                    if 'revenue' in df.columns:
                        df['gross_profit'] = df['revenue']
                        modified = True
                elif df['gross_profit'].isnull().any():
                    if 'revenue' in df.columns:
                        df['gross_profit'] = df['gross_profit'].fillna(df['revenue'])
                        modified = True
                
                # 2. Operating Income fallback
                if 'operating_income' not in df.columns:
                    if 'revenue' in df.columns:
                        df['operating_income'] = df['revenue']
                        modified = True
                elif df['operating_income'].isnull().any():
                    if 'revenue' in df.columns:
                        df['operating_income'] = df['operating_income'].fillna(df['revenue'])
                        modified = True
                
                # 3. Total Liabilities fallback
                if 'total_assets' in df.columns and 'equity' in df.columns:
                    if 'total_liabilities' not in df.columns:
                        df['total_liabilities'] = df['total_assets'] - df['equity']
                        modified = True
                    elif df['total_liabilities'].isnull().any():
                        df['total_liabilities'] = df['total_liabilities'].fillna(df['total_assets'] - df['equity'])
                        modified = True

                if modified:
                    df.to_parquet(p, index=False)
            except Exception:
                continue

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    symbols = get_target_symbols()
    data_manager = ParquetManager(base_path='data')
    config = load_api_config()
    finmind_client = FinMindClient(api_token=config['finmind']['token'])
    start_date, end_date = calculate_date_range()
    
    # 1. Diagnostics
    gaps = find_gaps(symbols, data_manager)
    all_fund_missing = gaps['net_income'].union(gaps['operating_cash_flow']).union(gaps['fundamental_file'])
    
    logger.info(f"Target stocks: {len(symbols)}")
    logger.info(f"Stocks needing fundamental healing: {len(all_fund_missing)}")
    
    # 2. Re-collect missing data
    if all_fund_missing:
        logger.info(f"Starting aggressive re-collection for: {sorted(list(all_fund_missing))}")
        for symbol in tqdm(sorted(list(all_fund_missing)), desc="Healing API"):
            try:
                data = finmind_client.get_comprehensive_fundamentals(symbol, start_date, end_date)
                merged = merge_fundamental_data(data)
                if not merged.empty:
                    data_manager.write_fundamental_data(merged, symbol)
                    logger.info(f"Successfully healed {symbol}")
            except Exception as e:
                logger.error(f"Failed to heal {symbol} from API: {e}")
                
    # 3. Local Fixes & Standardization
    apply_local_fixes(symbols)
    fix_nan_symbols()
    standardize_tech_files()
    
    logger.info("Healing process complete. Run scripts/comprehensive_check.py to verify.")

if __name__ == "__main__":
    main()
