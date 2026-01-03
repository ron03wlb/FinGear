"""
市場數據收集腳本 (籌碼面與技術面)

主要功能：
1. 抓取每日行情 (OHLCV) -> data/history
2. 抓取三大法人買賣超 -> data/chips
3. 抓取大戶持股比例 -> data/shareholding
4. 支援斷點續傳與自動略過已抓取數據

使用方法:
python scripts/collect_market_data.py --days 180
"""

import os
import sys
import json
import logging
import argparse
import pandas as pd
from datetime import datetime, timedelta
from tqdm import tqdm

# 加入專案路徑
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.finmind_client import FinMindClient
from src.parquet_manager import ParquetManager

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("collect_market_data.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_api_config():
    """載入 API Token"""
    config_path = os.path.join(project_root, 'config', 'api_keys.json')
    if not os.path.exists(config_path):
        logger.warning(f"找不到 API 設定檔: {config_path}")
        return None
    with open(config_path, 'r') as f:
        return json.load(f).get('finmind', {}).get('token')

def extract_symbols_from_doc():
    """從 500_stocks.txt 提取代碼"""
    doc_path = os.path.join(project_root, 'docs', '500_stocks.txt')
    symbols = []
    if os.path.exists(doc_path):
        with open(doc_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if parts and len(parts[0]) >= 4:
                    symbols.append(parts[0])
    return symbols

def main():
    parser = argparse.ArgumentParser(description='收集市場籌碼與技術面數據')
    parser.get_market_data = parser.add_argument_group('Data Range')
    parser.add_argument('--symbols', nargs='+', help='指定股票代碼 (選填)')
    parser.add_argument('--days', type=int, default=180, help='往前抓取的交易日天數 (預設 180 天)')
    parser.add_argument('--force', action='store_true', help='強制重新抓取')
    args = parser.parse_args()

    # 1. 初始化
    token = load_api_config()
    client = FinMindClient(api_token=token)
    pm = ParquetManager(base_path=os.path.join(project_root, 'data'))
    
    symbols = args.symbols if args.symbols else extract_symbols_from_doc()
    if not symbols:
        logger.error("沒有找到有效的股票代碼")
        return

    # 2. 計算日期範圍
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    
    logger.info(f"開始收集數據: {start_date} 至 {end_date}")
    logger.info(f"股票池總量: {len(symbols)} 檔")

    success_count = 0
    
    for symbol in tqdm(symbols, desc="收集市場數據"):
        try:
            # 檢查是否需要抓取 (檢查 price 數據作為基礎標誌)
            if not args.force:
                price_df = pm.read_symbol_partition(symbol)
                # 如果已有數據且最新日期在 3 天內，則跳過
                if not price_df.empty:
                    latest_date = pd.to_datetime(price_df['date'].max())
                    if (datetime.now() - latest_date).days < 3:
                        logger.debug(f"跳過 {symbol} (數據已是最新)")
                        continue

            # A. 每日價格 (Technical)
            df_price = client.get_daily_price(symbol, start_date, end_date)
            if not df_price.empty:
                # 映射 FinMind 欄位到標準 OHLCV
                price_mapping = {
                    'max': 'high',
                    'min': 'low',
                    'Trading_Volume': 'volume'
                }
                df_price.rename(columns=price_mapping, inplace=True)
                pm.write_symbol_partition(df_price, symbol)
            
            # B. 三大法人 (Chip Layer 2)
            df_chips = client.get_institutional_investors(symbol, start_date, end_date)
            if not df_chips.empty:
                # 計算買賣差額
                if 'diff' not in df_chips.columns:
                    df_chips['diff'] = df_chips['buy'] - df_chips['sell']
                
                # 轉置數據 (從長格式轉為寬格式) - 使用 pivot_table 以防原始數據有重複
                # FinMind names: ['Foreign_Investor', 'Investment_Trust', 'Dealer_self', 'Dealer_Hedging']
                pivoted = df_chips.pivot_table(index='date', columns='name', values='diff', aggfunc='sum')
                pivoted.reset_index(inplace=True)
                pivoted.columns.name = None
                
                # 標準化欄位名稱 (更精確的匹配以避免重複)
                rename_map = {}
                for col in pivoted.columns:
                    c_low = col.lower()
                    if c_low == 'foreign_investor': rename_map[col] = 'foreign_net'
                    elif 'investment_trust' in c_low or 'trust' in c_low: rename_map[col] = 'trust_net'
                    elif c_low == 'dealer_self' or c_low == 'dealer' or c_low == 'dealer_self': rename_map[col] = 'dealer_net'
                    elif 'hedging' in c_low: rename_map[col] = 'dealer_hedge_net'
                
                pivoted.rename(columns=rename_map, inplace=True)
                
                # 若仍有重複列名（如多個 dealer 相關），則進行聚合 (Pandas 3.0+ 不支援 axis=1)
                pivoted = pivoted.set_index('date')
                pivoted = pivoted.T.groupby(level=0).sum().T.reset_index()
                
                # 確保核心欄位存在
                for col in ['foreign_net', 'trust_net', 'dealer_net']:
                    if col not in pivoted.columns:
                        pivoted[col] = 0
                
                pivoted['total_net'] = pivoted.get('foreign_net', 0) + pivoted.get('trust_net', 0) + pivoted.get('dealer_net', 0)
                pm.write_chip_data(symbol, pivoted)

            # C. 大戶持股 (Chip Layer 2)
            df_share = client.get_shareholding(symbol, start_date, end_date)
            if not df_share.empty:
                # 聚合 400 張以上持股
                if 'HoldingSharesLevel' in df_share.columns:
                    # 轉換 Level 為數字
                    df_share['level_int'] = pd.to_numeric(df_share['HoldingSharesLevel'], errors='coerce')
                    major_only = df_share[df_share['level_int'] >= 11].groupby('date')['Percent'].sum().reset_index()
                    major_only.rename(columns={'Percent': 'major_ratio'}, inplace=True)
                    pm.write_shareholding_data(symbol, major_only)
                else:
                    pm.write_shareholding_data(symbol, df_share)

            success_count += 1
            
        except Exception as e:
            logger.error(f"收集 {symbol} 數據失敗: {e}")
            continue

    logger.info(f"收集完成！成功: {success_count}/{len(symbols)}")

if __name__ == '__main__':
    main()
