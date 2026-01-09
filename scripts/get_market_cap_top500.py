"""
取得市值 Top 500 股票清單

功能：
1. 取得所有上市櫃股票資訊
2. 批次查詢最新市值資料
3. 排序並取前 500 檔
4. 輸出至 CSV 檔案
"""

import sys
import os
import pandas as pd
import logging
import argparse
import time
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.finmind_client import FinMindClient

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

def get_top_500(client: FinMindClient, date: str = None) -> pd.DataFrame:
    """
    取得市值 Top 500 股票
    """
    logger = logging.getLogger(__name__)
    
    # 1. 取得所有上市櫃股票
    logger.info("正在取得股票基本資訊...")
    stock_info = client.get_stock_list(market="all")
    # 僅保留上市與上櫃股票，並排除權證、ETF (代號通常大於 4 碼或包含英文字母)
    mask = (stock_info['type'].isin(['twse', 'tpex'])) & (stock_info['stock_id'].str.len() == 4) & (stock_info['stock_id'].str.isdigit())
    valid_stocks_df = stock_info[mask]
    valid_stocks = valid_stocks_df['stock_id'].tolist()
    logger.info(f"過濾後總計 {len(valid_stocks)} 檔普通股股票")

    # 2. 設定日期範圍
    if date is None:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
    else:
        end_date = datetime.strptime(date, '%Y-%m-%d')
        start_date = end_date - timedelta(days=7)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    # 3. 批次取得市值資料
    logger.info(f"正在取得市值資料 ({start_str} ~ {end_str})...")
    market_values = []
    batch_size = 50
    
    for i in range(0, len(valid_stocks), batch_size):
        batch = valid_stocks[i:i+batch_size]
        try:
            df = client.get_market_value(
                symbol_list=batch,
                start_date=start_str,
                end_date=end_str
            )
            if df is not None and not df.empty:
                market_values.append(df)
            
            if (i // batch_size) % 5 == 0:
                logger.info(f"進度: {min(i + batch_size, len(valid_stocks))}/{len(valid_stocks)}")
        except Exception as e:
            logger.error(f"批次起始於 {batch[0]} 失敗: {e}")
            continue

    if not market_values:
        logger.error("未能取得任何市值資料")
        return pd.DataFrame()

    # 4. 合併並處理
    all_data = pd.concat(market_values, ignore_index=True)
    latest_date = all_data['date'].max()
    logger.info(f"使用最新日期資料: {latest_date}")
    
    latest_data = all_data[all_data['date'] == latest_date].copy()
    latest_data = latest_data.sort_values('market_value', ascending=False)
    
    # 5. 加入股票名稱與排名
    top_500 = latest_data.head(500).copy()
    top_500['rank'] = range(1, len(top_500) + 1)
    
    top_500 = top_500.merge(
        stock_info[['stock_id', 'stock_name']],
        on='stock_id',
        how='left'
    )
    
    return top_500[['stock_id', 'stock_name', 'market_value', 'rank', 'date']]

def main():
    parser = argparse.ArgumentParser(description="取得市值 Top 500 股票")
    parser.add_argument("--output", type=str, default="data/temp/top500_latest.csv", help="輸出路徑")
    parser.add_argument("--date", type=str, help="指定日期 (YYYY-MM-DD)")
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger(__name__)

    # Load config
    config_path = Path("config/api_keys.json")
    if not config_path.exists():
        logger.error("找不到 config/api_keys.json")
        return

    with open(config_path, "r") as f:
        config = json.load(f)
    
    token = config.get("finmind", {}).get("token", "")
    client = FinMindClient(api_token=token)

    # Execute
    top_500_df = get_top_500(client, date=args.date)
    
    if not top_500_df.empty:
        # Ensure directory exists
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        top_500_df.to_csv(args.output, index=False, encoding='utf-8-sig')
        logger.info(f"✅ 成功儲存 Top 500 清單至 {args.output}")
        logger.info(f"前 5 名:\n{top_500_df.head().to_string(index=False)}")
    else:
        logger.error("執行失敗，未產生清單")

if __name__ == "__main__":
    main()
