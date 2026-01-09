
import logging
import pandas as pd
from pathlib import Path
from src.parquet_manager import ParquetManager
from src.factors import FactorEngine
from src.screener import StockScreener

def diagnose():
    # Setup logging to be silent
    logging.basicConfig(level=logging.ERROR)
    
    data_manager = ParquetManager(base_path='data')
    factor_engine = FactorEngine(data_manager=data_manager)
    screener = StockScreener(factor_engine=factor_engine, data_manager=data_manager)
    
    history_path = Path('data/history')
    universe = sorted([d.name.split('=')[1] for d in history_path.iterdir() if d.is_dir() and 'symbol=' in d.name])
    
    print(f"Total universe size: {len(universe)} stocks")
    
    l1_candidates = []
    pe_filtered_count = 0
    data_error_count = 0
    
    for symbol in universe:
        try:
            details = factor_engine.calculate_fundamental_details(symbol)
            pe_score = details['factors'].get('pe_relative', {}).get('score', 0)
            
            if pe_score < 4:
                pe_filtered_count += 1
                continue
                
            l1_candidates.append({
                'symbol': symbol,
                'fundamental_score': details['total_score'],
                'pe_score': pe_score
            })
        except Exception:
            data_error_count += 1
            
    df_l1 = pd.DataFrame(l1_candidates).sort_values('fundamental_score', ascending=False)
    print(f"Passed Layer 1 PE Filter (PE <= Mean): {len(df_l1)} stocks")
    print(f"Filtered out by PE: {pe_filtered_count} stocks")
    print(f"Errors/Missing data: {data_error_count} stocks")
    
    top_30 = df_l1.head(30)
    print(f"\nTop 30 Fundamental Stocks (Candidates for Layer 2):")
    
    l2_passed = []
    l2_dropped = []
    
    for _, row in top_30.iterrows():
        symbol = row['symbol']
        chip_df = data_manager.read_chip_data(symbol)
        if chip_df.empty or len(chip_df) < 5:
            l2_dropped.append(symbol)
            continue
        l2_passed.append(symbol)
        
    print(f"Layer 2 Passed: {len(l2_passed)} stocks")
    print(f"Layer 2 Dropped (Insufficient Chip Data): {len(l2_dropped)} stocks")
    if l2_dropped:
        print(f"Dropped Symbols: {', '.join(l2_dropped)}")
        
    print(f"\nFinal count of stocks passing all criteria: {len(l2_passed)}")

if __name__ == "__main__":
    diagnose()
