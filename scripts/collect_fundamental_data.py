"""
FinMind 基本面數據收集腳本

執行時機：首次運行或需要更新基本面數據時
功能：
    1. 從 FinMind API 抓取台股基本面數據
    2. 涵蓋過去 12 個月的季報、月營收數據
    3. 儲存至 Parquet 格式：data/fundamentals/symbol=XXXX/
    4. 支援斷點續傳（跳過已下載的股票）
    5. 進度追蹤與錯誤處理

參考：Implementation Plan - FinMind Integration
"""

import logging
import json
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.finmind_client import FinMindClient
from src.parquet_manager import ParquetManager


def load_api_config() -> dict:
    """
    載入 API 配置
    
    Returns:
        Configuration dictionary with FinMind token
        
    Raises:
        FileNotFoundError: Config file not found
        KeyError: FinMind token not in config
    """
    config_path = Path(__file__).parent.parent / 'config' / 'api_keys.json'
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            "Please create config/api_keys.json with your FinMind token."
        )
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    if 'finmind' not in config or 'token' not in config['finmind']:
        raise KeyError(
            "FinMind token not found in config.\n"
            "Please add 'finmind': {'token': 'YOUR_TOKEN'} to config/api_keys.json"
        )
    
    return config


def calculate_date_range() -> tuple[str, str]:
    """
    計算數據收集日期範圍（過去 18 個月，確保涵蓋 5 個季度）
    
    Returns:
        (start_date, end_date) in 'YYYY-MM-DD' format
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=18 * 30)  # 約 18 個月
    
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')


def get_stock_universe(finmind_client: FinMindClient, market: str = "all") -> List[str]:
    """
    獲取台股股票清單
    
    Args:
        finmind_client: FinMind API client
        market: Market filter ('TSE', 'OTC', or 'all')
        
    Returns:
        List of stock symbols
        
    Raises:
        Exception: Failed to fetch stock list
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Fetching stock list for market: {market}")
    
    try:
        all_stocks = finmind_client.get_stock_list(market=market)
        
        if 'stock_id' in all_stocks.columns:
            symbols = all_stocks['stock_id'].tolist()
        else:
            raise ValueError("Stock list missing 'stock_id' column")
        
        logger.info(f"Retrieved {len(symbols)} stocks from market: {market}")
        return symbols
        
    except Exception as e:
        logger.error(f"Failed to fetch stock universe: {e}")
        raise


def get_already_downloaded_symbols(data_manager: ParquetManager) -> set[str]:
    """
    獲取已下載基本面數據的股票列表（用於斷點續傳）
    
    Args:
        data_manager: Parquet data manager
        
    Returns:
        Set of stock symbols already downloaded
    """
    fundamentals_path = data_manager.fundamentals_path
    
    if not fundamentals_path.exists():
        return set()
    
    downloaded = set()
    for symbol_dir in fundamentals_path.iterdir():
        if symbol_dir.is_dir() and symbol_dir.name.startswith('symbol='):
            symbol = symbol_dir.name.split('=')[1]
            # Check if data file exists and has content
            data_file = symbol_dir / 'data.parquet'
            if data_file.exists() and data_file.stat().st_size > 0:
                downloaded.add(symbol)
    
    return downloaded


def merge_fundamental_data(comprehensive_data: dict) -> pd.DataFrame:
    """
    合併各類基本面數據為統一格式
    
    FinMind returns data in "long" format (type-value pairs),
    need to pivot to "wide" format with separate columns for each metric.
    
    Args:
        comprehensive_data: Dictionary containing financial_statement, balance_sheet, 
                          cash_flow, monthly_revenue DataFrames
                          
    Returns:
        Merged DataFrame with unified schema for factor calculation
    """
    logger = logging.getLogger(__name__)
    
    # Extract individual dataframes
    fin_stmt = comprehensive_data.get('financial_statement', pd.DataFrame())
    balance = comprehensive_data.get('balance_sheet', pd.DataFrame())
    cash_flow = comprehensive_data.get('cash_flow', pd.DataFrame())
    revenue = comprehensive_data.get('monthly_revenue', pd.DataFrame())
    
    # If all empty, return empty DataFrame
    if all(df.empty for df in [fin_stmt, balance, cash_flow]):
        logger.warning("All fundamental data sources are empty")
        return pd.DataFrame()
    
    # Helper function to pivot long-format data to wide-format
    def pivot_financial_data(df: pd.DataFrame) -> pd.DataFrame:
        """Pivot FinMind long-format data to wide-format"""
        if df.empty or 'type' not in df.columns or 'value' not in df.columns:
            return pd.DataFrame()
        
        # Pivot: rows=date, columns=type, values=value
        pivoted = df.pivot(index='date', columns='type', values='value')
        pivoted.reset_index(inplace=True)
        return pivoted
    
    # Pivot each data source
    fin_pivot = pivot_financial_data(fin_stmt)
    balance_pivot = pivot_financial_data(balance)
    cf_pivot = pivot_financial_data(cash_flow)
    
    # Start merging (use quarterly data as base)
    if not fin_pivot.empty:
        merged = fin_pivot.copy()
        
        # Merge balance sheet
        if not balance_pivot.empty:
            merged = pd.merge(
                merged, balance_pivot,
                on='date', how='outer', suffixes=('', '_balance')
            )
        
        # Merge cash flow
        if not cf_pivot.empty:
            merged = pd.merge(
                merged, cf_pivot,
                on='date', how='outer', suffixes=('', '_cf')
            )
    elif not balance_pivot.empty:
        merged = balance_pivot.copy()
        if not cf_pivot.empty:
            merged = pd.merge(
                merged, cf_pivot,
                on='date', how='outer', suffixes=('', '_cf')
            )
    elif not cf_pivot.empty:
        merged = cf_pivot.copy()
    else:
        logger.warning("All pivoted data is empty")
        return pd.DataFrame()
    
    # Map FinMind column names to our expected schema
    # Reference: https://finmind.github.io/tutor/TaiwanMarket/Financial/
    column_mapping = {
        # Income Statement (損益表)
        'Revenue': 'revenue',                          # 營業收入
        'GrossProfit': 'gross_profit',                 # 毛利
        'NetIncome': 'net_income',                     # 本期淨利（稅後）
        'OperatingIncome': 'operating_income',         # 營業利益
        'OperatingExpenses': 'operating_expense',      # 營業費用
        'EPS': 'eps',                                   # 每股盈餘
        
        # Balance Sheet (資產負債表)
        'TotalAssets': 'total_assets',                  # 總資產
        'TotalLiabilities': 'total_liabilities',        # 總負債
        'Equity': 'equity',                             # 股東權益
        
        # Cash Flow (現金流量表)
        'CashProvidedByOperatingActivities': 'operating_cash_flow',     # 營業現金流
        'CashProvidedByInvestingActivities': 'investing_cash_flow',     # 投資現金流
        'CashProvidedByFinancingActivities': 'financing_cash_flow',     # 融資現金流
        'CashAndCashEquivalentsAtEndOfPeriod': 'cash_equivalents',     # 期末現金
    }
    
    # Rename columns
    merged.rename(columns=column_mapping, inplace=True)
    
    # Calculate derived fields if not present
    # Capital expenditure (資本支出) = negative of investing cash flow (approximation)
    if 'capital_expenditure' not in merged.columns and 'investing_cash_flow' in merged.columns:
        merged['capital_expenditure'] = -merged['investing_cash_flow']  # Usually negative
    
    # Keep only essential columns for factor calculation
    essential_cols = [
        'date',
        'revenue',             # 營業收入
        'gross_profit',        # 毛利
        'net_income',          # 稅後淨利
        'operating_income',    # 營業利益
        'eps',                 # 每股盈餘
        'equity',              # 股東權益
        'total_assets',        # 總資產
        'total_liabilities',   # 總負債
        'operating_cash_flow', # 營業現金流
        'investing_cash_flow', # 投資現金流
        'capital_expenditure', # 資本支出
    ]
    
    # Filter to only columns that exist
    available_cols = [col for col in essential_cols if col in merged.columns]
    merged = merged[available_cols].copy()
    
    # Ensure date is datetime
    if 'date' in merged.columns:
        merged['date'] = pd.to_datetime(merged['date'])
    
    # Sort by date and remove duplicates
    merged = merged.sort_values('date').drop_duplicates(subset=['date'], keep='last')
    
    logger.info(f"Merged data shape: {merged.shape}, columns: {list(merged.columns)}")
    
    return merged



def collect_fundamental_data(
    symbols: List[str],
    finmind_client: FinMindClient,
    data_manager: ParquetManager,
    start_date: str,
    end_date: str,
    skip_existing: bool = True
) -> tuple[int, int]:
    """
    批次收集基本面數據
    
    Args:
        symbols: List of stock symbols
        finmind_client: FinMind API client
        data_manager: Parquet data manager
        start_date: Start date for data collection
        end_date: End date for data collection
        skip_existing: Skip symbols that already have data
        
    Returns:
        (success_count, failure_count) tuple
    """
    logger = logging.getLogger(__name__)
    
    # Get already downloaded symbols
    if skip_existing:
        already_downloaded = get_already_downloaded_symbols(data_manager)
        symbols = [s for s in symbols if s not in already_downloaded]
        logger.info(f"Skipping {len(already_downloaded)} already downloaded stocks")
    
    if not symbols:
        logger.info("No new stocks to download.")
        return 0, 0
    
    logger.info(f"Starting data collection for {len(symbols)} stocks ({start_date} to {end_date})")
    
    success_count = 0
    failure_count = 0
    
    # Progress bar
    with tqdm(total=len(symbols), desc="Collecting fundamental data", unit="stock") as pbar:
        for symbol in symbols:
            try:
                # Fetch comprehensive fundamental data
                data = finmind_client.get_comprehensive_fundamentals(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                
                # Merge data sources
                merged_data = merge_fundamental_data(data)
                
                if merged_data.empty:
                    logger.warning(f"No data available for {symbol}, skipping")
                    pbar.update(1)
                    continue
                
                # Validate minimum data requirement (at least 2 quarters)
                if len(merged_data) < 2:
                    logger.warning(
                        f"Insufficient data for {symbol} "
                        f"(only {len(merged_data)} quarters), skipping"
                    )
                    pbar.update(1)
                    continue
                
                # Save to Parquet
                data_manager.write_fundamental_data(symbol, merged_data)
                success_count += 1
                
            except Exception as e:
                logger.error(f"Failed to collect data for {symbol}: {e}")
                failure_count += 1
            
            finally:
                pbar.update(1)
                pbar.set_postfix({
                    'success': success_count,
                    'failed': failure_count
                })
    
    return success_count, failure_count


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='Collect Taiwan stock fundamental data from FinMind API'
    )
    parser.add_argument(
        '--market',
        choices=['TSE', 'OTC', 'all'],
        default='all',
        help='Market filter: TSE (上市), OTC (上櫃), or all'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of stocks to fetch (for testing)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-download even if data exists'
    )
    parser.add_argument(
        '--symbols',
        nargs='+',
        help='Specific symbols to download (e.g., --symbols 2330 2317)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/finmind_collection.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        logger.info("Loading API configuration...")
        config = load_api_config()
        
        # Initialize clients
        finmind_client = FinMindClient(api_token=config['finmind']['token'])
        data_manager = ParquetManager(base_path='data')
        
        # Calculate date range
        start_date, end_date = calculate_date_range()
        logger.info(f"Data collection period: {start_date} to {end_date}")
        
        # Get stock universe
        if args.symbols:
            # Use user-specified symbols
            symbols = args.symbols
            logger.info(f"Using user-specified symbols: {symbols}")
        else:
            # Fetch from FinMind
            symbols = get_stock_universe(finmind_client, market=args.market)
            
            # Apply limit if specified
            if args.limit:
                symbols = symbols[:args.limit]
                logger.info(f"Limited to first {args.limit} stocks")
        
        # Collect data
        success_count, failure_count = collect_fundamental_data(
            symbols=symbols,
            finmind_client=finmind_client,
            data_manager=data_manager,
            start_date=start_date,
            end_date=end_date,
            skip_existing=not args.force
        )
        
        # Summary
        logger.info("=" * 60)
        logger.info("Data Collection Summary:")
        total = success_count + failure_count
        logger.info(f"  Total stocks processed: {total}")
        logger.info(f"  Successfully collected: {success_count}")
        logger.info(f"  Failed: {failure_count}")
        if total > 0:
            logger.info(f"  Success rate: {success_count / total * 100:.1f}%")
        else:
            logger.info("  No new stocks to process (all already downloaded or empty list)")
        logger.info("=" * 60)
        
        if failure_count > 0:
            logger.warning(f"{failure_count} stocks failed. Check logs for details.")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
