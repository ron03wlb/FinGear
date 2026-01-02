"""
每日數據更新腳本

執行時機：每日 15:00
功能：
    1. 抓取日行情、法人、集保數據
    2. 數據驗證與清洗
    3. 寫入 Parquet 分區
    4. ETL 轉置
    5. 清理舊數據

參考：Requirement/Implementation.md 第 4.1 節
"""

import logging
import json
import os
import pandas as pd
from datetime import datetime, date, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.api_client import ShioajiClient
from src.parquet_manager import ParquetManager
from src.scrapers import ChipDataScraper
from src.utils import setup_logging

def daily_update(target_date: str = None):
    """
    每日數據更新主流程
    """
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")
        
    logger = logging.getLogger(__name__)
    logger.info(f"開始數據更新: {target_date}")

    # 1. 載入配置
    config_path = Path('config/api_keys.json')
    with open(config_path, 'r') as f:
        keys = json.load(f)
    
    api_key = keys['shioaji']['api_key']
    secret_key = keys['shioaji']['secret_key']

    # 2. 初始化組件
    client = ShioajiClient(api_key, secret_key)
    manager = ParquetManager(base_path='data')
    scraper = ChipDataScraper()

    try:
        # --- 3. 抓取法人及大戶數據 (Real Data) ---
        logger.info("正在抓取法人買賣超數據...")
        inst_df = scraper.scrape_institutional_trades(target_date)
        if not inst_df.empty:
            for symbol, group in inst_df.groupby('symbol'):
                manager.write_chip_data(symbol, group)
            logger.info("法人買賣超數據更新完成")

        # 每週五或週末抓取集保大戶 (一週更新一次)
        # 這裡我們每次更新都嘗試抓取最新的大戶數據
        logger.info("正在抓取大戶持股數據...")
        share_df = scraper.scrape_tdcc_shareholding()
        if not share_df.empty:
            for symbol, group in share_df.groupby('symbol'):
                manager.write_shareholding_data(symbol, group)
            logger.info("大戶持股數據更新完成")

        # --- 4. 抓取日行情 (Shioaji) ---
        with client:
            # 取得 Top 名單 (範例：先抓 2330, 2317, 2454 等權值股)
            symbols = ["2330", "2317", "2454", "2308", "2303", "2881", "2882"] 
            logger.info(f"準備從 Shioaji 抓取 {len(symbols)} 檔股票數據")

            all_data = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_symbol = {executor.submit(client.get_historical_data, s, target_date, target_date): s for s in symbols}
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        df = future.result()
                        if not df.empty:
                            all_data.append(df)
                    except Exception as exc:
                        logger.error(f"{symbol} 抓取失敗: {exc}")

            if not all_data:
                logger.warning(f"{target_date} 沒有抓取到價格數據，可能為非交易日。")
            else:
                # 合併數據並寫入時間分區
                final_df = pd.concat(all_data)
                manager.write_time_partition(final_df, target_date)
                # ETL 轉置
                manager.transpose_to_symbol_partition(target_date)
            
            logger.info(f"{target_date} 數據更新流程結束。")

    except Exception as e:
        logger.error(f"數據更新失敗: {e}", exc_info=True)



def main():
    """主函數"""
    # 設置日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 手動執行一次更新（今日）
    daily_update()



if __name__ == '__main__':
    main()
