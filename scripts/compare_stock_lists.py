"""
比對新舊股票清單，找出需新增與移除的股票
"""

import argparse
import logging
import pandas as pd
from pathlib import Path

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    parser = argparse.ArgumentParser(description="比對新舊清單")
    parser.add_argument("--current", type=str, default="config/top_stocks.txt", help="現有名單路徑")
    parser.add_argument("--new", type=str, required=True, help="新清單 (CSV) 路徑")
    parser.add_argument("--output", type=str, default="data/temp/new_stocks.txt", help="輸出待補股票清單")
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger(__name__)

    # 1. 讀取現有名單
    current_path = Path(args.current)
    current_symbols = set()
    if current_path.exists():
        with open(current_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.split()
                if parts and parts[0].isdigit():
                    current_symbols.add(parts[0])
    logger.info(f"現有名單股票數: {len(current_symbols)}")

    # 2. 讀取新清單
    new_df = pd.read_csv(args.new)
    new_symbols = set(new_df['stock_id'].astype(str))
    logger.info(f"新清單股票數: {len(new_symbols)}")

    # 3. 比對
    to_add = sorted(list(new_symbols - current_symbols))
    to_remove = sorted(list(current_symbols - new_symbols))
    unchanged = sorted(list(current_symbols & new_symbols))

    logger.info(f"需新增: {len(to_add)} 檔")
    logger.info(f"需移除: {len(to_remove)} 檔")
    logger.info(f"保持不變: {len(unchanged)} 檔")

    # 4. 輸出需新增的名單
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for s in to_add:
            f.write(f"{s}\n")
    
    logger.info(f"✅ 待補股票代號已存入 {args.output}")

if __name__ == "__main__":
    main()
