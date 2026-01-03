"""
完善資料庫腳本

功能：
    1. 收集所有 top_stocks 的歷史價格資料
    2. 收集籌碼數據（法人買賣超、大戶持股）
    3. 驗證資料完整性
    4. 生成資料狀況報告

執行方式：
    python scripts/complete_database.py [--lookback-days 365] [--force]
"""

import logging
import json
import argparse
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Set, Dict
import pandas as pd
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api_client import ShioajiClient
from src.parquet_manager import ParquetManager
from src.scrapers import ChipDataScraper
from concurrent.futures import ThreadPoolExecutor, as_completed


def setup_logging() -> logging.Logger:
    """設置日誌"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/complete_database.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def load_top_stocks() -> List[str]:
    """
    從配置文件載入 Top 股票清單
    
    Returns:
        List of stock symbols
    """
    config_path = Path('config/top_stocks.txt')
    
    if not config_path.exists():
        raise FileNotFoundError(f"Stock list not found: {config_path}")
    
    symbols = []
    with open(config_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Extract 4-digit stock code
                match = re.match(r'^(\d{4})', line)
                if match:
                    symbols.append(match.group(1))
    
    return symbols


def get_missing_symbols(
    all_symbols: List[str],
    data_manager: ParquetManager,
    data_type: str
) -> List[str]:
    """
    找出缺少資料的股票
    
    Args:
        all_symbols: All stock symbols to check
        data_manager: ParquetManager instance
        data_type: 'history', 'chips', or 'shareholding'
        
    Returns:
        List of symbols missing data
    """
    if data_type == 'history':
        data_path = data_manager.history_path
    elif data_type == 'chips':
        data_path = data_manager.chips_path
    elif data_type == 'shareholding':
        data_path = data_manager.shareholding_path
    else:
        raise ValueError(f"Invalid data_type: {data_type}")
    
    existing = set()
    if data_path.exists():
        for symbol_dir in data_path.iterdir():
            if symbol_dir.is_dir() and symbol_dir.name.startswith('symbol='):
                symbol = symbol_dir.name.split('=')[1]
                # Check if has data
                if list(symbol_dir.glob('*.parquet')):
                    existing.add(symbol)
    
    missing = [s for s in all_symbols if s not in existing]
    return missing


def collect_price_history(
    symbols: List[str],
    client: ShioajiClient,
    data_manager: ParquetManager,
    lookback_days: int = 365,
    logger: logging.Logger = None
) -> Dict[str, int]:
    """
    收集歷史價格資料
    
    Args:
        symbols: Stock symbols to collect
        client: ShioajiClient instance
        data_manager: ParquetManager instance
        lookback_days: Number of days to look back
        logger: Logger instance
        
    Returns:
        Dictionary with success/failure counts
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    logger.info(f"收集價格歷史資料：{start_str} to {end_str}")
    logger.info(f"股票數: {len(symbols)}")
    
    success = 0
    failure = 0
    
    with tqdm(total=len(symbols), desc="Collecting price history", unit="stock") as pbar:
        for symbol in symbols:
            try:
                # Fetch historical data
                df = client.get_historical_data(symbol, start_str, end_str)
                
                if df.empty:
                    logger.warning(f"{symbol}: No price data available")
                    pbar.update(1)
                    continue
                
                # Write each date to daily partition
                for date_str in df['date'].dt.strftime('%Y-%m-%d').unique():
                    date_df = df[df['date'].dt.strftime('%Y-%m-%d') == date_str]
                    data_manager.write_time_partition(date_df, date_str)
                
                # Transpose to symbol partition
                for date_str in df['date'].dt.strftime('%Y-%m-%d').unique():
                    data_manager.transpose_to_symbol_partition(date_str)
                
                success += 1
                
            except Exception as e:
                logger.error(f"{symbol} 價格資料收集失敗: {e}")
                failure += 1
            
            finally:
                pbar.update(1)
                pbar.set_postfix({'success': success, 'failed': failure})
    
    return {'success': success, 'failure': failure}


def collect_chip_data(
    symbols: List[str],
    scraper: ChipDataScraper,
    data_manager: ParquetManager,
    lookback_days: int = 90,
    logger: logging.Logger = None
) -> Dict[str, int]:
    """
    收集籌碼資料（法人買賣超）
    
    Args:
        symbols: Stock symbols to collect
        scraper: ChipDataScraper instance
        data_manager: ParquetManager instance
        lookback_days: Number of days to look back
        logger: Logger instance
        
    Returns:
        Dictionary with success/failure counts
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info(f"收集最近 {lookback_days} 天的籌碼資料")
    logger.info(f"股票數: {len(symbols)}")
    
    success = 0
    failure = 0
    
    # Generate date list
    end_date = datetime.now()
    dates = []
    for i in range(lookback_days):
        date = end_date - timedelta(days=i)
        # Only weekdays (Mon-Fri)
        if date.weekday() < 5:
            dates.append(date.strftime('%Y-%m-%d'))
    
    logger.info(f"將收集 {len(dates)} 個交易日的籌碼資料")
    
    with tqdm(total=len(dates), desc="Collecting chip data", unit="date") as pbar:
        for date_str in dates:
            try:
                # Scrape institutional trades for this date
                inst_df = scraper.scrape_institutional_trades(date_str)
                
                if inst_df.empty:
                    logger.debug(f"{date_str}: No chip data (may be non-trading day)")
                    pbar.update(1)
                    continue
                
                # Filter to our symbols only
                inst_df = inst_df[inst_df['symbol'].isin(symbols)]
                
                # Write to parquet
                for symbol, group in inst_df.groupby('symbol'):
                    data_manager.write_chip_data(symbol, group)
                
                success += 1
                
            except Exception as e:
                logger.error(f"{date_str} 籌碼資料收集失敗: {e}")
                failure += 1
            
            finally:
                pbar.update(1)
                pbar.set_postfix({'success': success, 'failed': failure})
    
    return {'success': success, 'failure': failure}


def collect_shareholding_data(
    symbols: List[str],
    scraper: ChipDataScraper,
    data_manager: ParquetManager,
    logger: logging.Logger = None
) -> Dict[str, int]:
    """
    收集大戶持股資料（集保資料，每週更新）
    
    Args:
        symbols: Stock symbols to collect
        scraper: ChipDataScraper instance
        data_manager: ParquetManager instance
        logger: Logger instance
        
    Returns:
        Dictionary with success/failure counts
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info(f"收集大戶持股資料")
    
    try:
        # Scrape latest shareholding data
        share_df = scraper.scrape_tdcc_shareholding()
        
        if share_df.empty:
            logger.warning("無法取得大戶持股資料")
            return {'success': 0, 'failure': 1}
        
        # Filter to our symbols
        share_df = share_df[share_df['symbol'].isin(symbols)]
        
        # Write to parquet
        for symbol, group in share_df.groupby('symbol'):
            data_manager.write_shareholding_data(symbol, group)
        
        success_count = share_df['symbol'].nunique()
        logger.info(f"成功收集 {success_count} 檔股票的大戶持股資料")
        
        return {'success': success_count, 'failure': 0}
        
    except Exception as e:
        logger.error(f"大戶持股資料收集失敗: {e}")
        return {'success': 0, 'failure': 1}


def generate_data_report(
    all_symbols: List[str],
    data_manager: ParquetManager,
    logger: logging.Logger
) -> None:
    """
    生成資料狀況報告
    
    Args:
        all_symbols: All symbols in the universe
        data_manager: ParquetManager instance
        logger: Logger instance
    """
    logger.info("=" * 60)
    logger.info("資料庫狀況報告")
    logger.info("=" * 60)
    
    # Fundamentals
    fund_symbols = set()
    if data_manager.fundamentals_path.exists():
        for symbol_dir in data_manager.fundamentals_path.glob('symbol=*'):
            symbol = symbol_dir.name.split('=')[1]
            if list(symbol_dir.glob('*.parquet')):
                fund_symbols.add(symbol)
    
    # History
    hist_symbols = set()
    if data_manager.history_path.exists():
        for symbol_dir in data_manager.history_path.glob('symbol=*'):
            symbol = symbol_dir.name.split('=')[1]
            if list(symbol_dir.glob('*.parquet')):
                hist_symbols.add(symbol)
    
    # Chips
    chip_symbols = set()
    if data_manager.chips_path.exists():
        for symbol_dir in data_manager.chips_path.glob('symbol=*'):
            symbol = symbol_dir.name.split('=')[1]
            if list(symbol_dir.glob('*.parquet')):
                chip_symbols.add(symbol)
    
    # Shareholding
    share_symbols = set()
    if data_manager.shareholding_path.exists():
        for symbol_dir in data_manager.shareholding_path.glob('symbol=*'):
            symbol = symbol_dir.name.split('=')[1]
            if list(symbol_dir.glob('*.parquet')):
                share_symbols.add(symbol)
    
    # Daily partitions
    daily_dates = list(data_manager.daily_path.glob('date=*'))
    
    total = len(all_symbols)
    logger.info(f"\n股票清單總數: {total}")
    logger.info(f"\n1. 基本面資料 (Fundamentals):")
    logger.info(f"   - 已收集: {len(fund_symbols)}/{total} ({len(fund_symbols)/total*100:.1f}%)")
    logger.info(f"   - 缺少: {total - len(fund_symbols)}")
    
    logger.info(f"\n2. 歷史價格 (History):")
    logger.info(f"   - 已收集: {len(hist_symbols)}/{total} ({len(hist_symbols)/total*100:.1f}%)")
    logger.info(f"   - 缺少: {total - len(hist_symbols)}")
    
    logger.info(f"\n3. 籌碼資料 (Chips):")
    logger.info(f"   - 已收集: {len(chip_symbols)}/{total} ({len(chip_symbols)/total*100:.1f}%)")
    logger.info(f"   - 缺少: {total - len(chip_symbols)}")
    
    logger.info(f"\n4. 大戶持股 (Shareholding):")
    logger.info(f"   - 已收集: {len(share_symbols)}/{total} ({len(share_symbols)/total*100:.1f}%)")
    logger.info(f"   - 缺少: {total - len(share_symbols)}")
    
    logger.info(f"\n5. 每日資料分區 (Daily):")
    logger.info(f"   - 日期數: {len(daily_dates)}")
    
    # Calculate completeness
    all_data_symbols = fund_symbols & hist_symbols & chip_symbols & share_symbols
    logger.info(f"\n完整資料的股票數: {len(all_data_symbols)}/{total} ({len(all_data_symbols)/total*100:.1f}%)")
    
    missing_any = set(all_symbols) - all_data_symbols
    if missing_any:
        logger.info(f"\n缺少至少一種資料的股票: {sorted(missing_any)}")
    
    logger.info("=" * 60)


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='Complete FinGear database with all required data'
    )
    parser.add_argument(
        '--lookback-days',
        type=int,
        default=365,
        help='Number of days to collect price history (default: 365)'
    )
    parser.add_argument(
        '--chip-days',
        type=int,
        default=90,
        help='Number of days to collect chip data (default: 90)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-download even if data exists'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Only generate data report without collecting'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging()
    
    try:
        logger.info("開始資料庫完善流程")
        
        # Load stock universe
        all_symbols = load_top_stocks()
        logger.info(f"載入股票清單: {len(all_symbols)} 檔股票")
        
        # Initialize managers
        data_manager = ParquetManager(base_path='data')
        
        # Generate initial report
        generate_data_report(all_symbols, data_manager, logger)
        
        if args.report_only:
            logger.info("僅生成報告模式，結束")
            return
        
        # Load API configuration
        config_path = Path('config/api_keys.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Initialize API clients
        shioaji_client = ShioajiClient(
            api_key=config['shioaji']['api_key'],
            secret_key=config['shioaji']['secret_key']
        )
        scraper = ChipDataScraper()
        
        # Step 1: Collect price history
        logger.info("\n" + "=" * 60)
        logger.info("步驟 1: 收集歷史價格資料")
        logger.info("=" * 60)
        
        missing_history = get_missing_symbols(all_symbols, data_manager, 'history')
        if args.force:
            missing_history = all_symbols
        
        if missing_history:
            logger.info(f"需要收集價格資料的股票: {len(missing_history)} 檔")
            with shioaji_client:
                price_result = collect_price_history(
                    missing_history,
                    shioaji_client,
                    data_manager,
                    args.lookback_days,
                    logger
                )
            logger.info(f"價格資料收集完成: 成功 {price_result['success']}, 失敗 {price_result['failure']}")
        else:
            logger.info("所有股票已有價格資料")
        
        # Step 2: Collect chip data
        logger.info("\n" + "=" * 60)
        logger.info("步驟 2: 收集籌碼資料")
        logger.info("=" * 60)
        
        missing_chips = get_missing_symbols(all_symbols, data_manager, 'chips')
        if args.force:
            missing_chips = all_symbols
        
        if missing_chips:
            logger.info(f"需要收集籌碼資料的股票: {len(missing_chips)} 檔")
            chip_result = collect_chip_data(
                missing_chips,
                scraper,
                data_manager,
                args.chip_days,
                logger
            )
            logger.info(f"籌碼資料收集完成: 成功 {chip_result['success']}, 失敗 {chip_result['failure']}")
        else:
            logger.info("所有股票已有籌碼資料")
        
        # Step 3: Collect shareholding data
        logger.info("\n" + "=" * 60)
        logger.info("步驟 3: 收集大戶持股資料")
        logger.info("=" * 60)
        
        share_result = collect_shareholding_data(
            all_symbols,
            scraper,
            data_manager,
            logger
        )
        logger.info(f"大戶持股資料收集完成: 成功 {share_result['success']}, 失敗 {share_result['failure']}")
        
        # Generate final report
        logger.info("\n")
        generate_data_report(all_symbols, data_manager, logger)
        
        logger.info("\n資料庫完善流程完成！")
        
    except Exception as e:
        logger.error(f"發生錯誤: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
