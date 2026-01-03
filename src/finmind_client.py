"""
FinMind API 客戶端模組

提供 FinMind API 的封裝，實現：
- Rate Limiter (3 requests/sec for free tier)
- Retry mechanism with exponential backoff
- Taiwan stock fundamental data fetching
- Financial statements, revenue, balance sheet, cash flow data

參考：Implementation Plan - FinMind Integration
"""

import time
import logging
import threading
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import pandas as pd
from FinMind.data import DataLoader

class RateLimiter:
    """
    API 請求速率限制器
    FinMind 免費版限制: 3 requests/second
    """
    def __init__(self, max_requests: int = 3, time_window: float = 1.0):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds (default 1.0 for per-second limit)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_timestamps: List[float] = []
        self.lock = threading.Lock()

    def wait_if_needed(self) -> None:
        """若超過速率限制則等待"""
        with self.lock:
            now = time.time()
            # 清理超時的時間戳
            self.request_timestamps = [
                ts for ts in self.request_timestamps 
                if now - ts < self.time_window
            ]
            
            if len(self.request_timestamps) >= self.max_requests:
                sleep_time = self.time_window - (now - self.request_timestamps[0])
                if sleep_time > 0:
                    logging.debug(f"Rate limit reached, waiting {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    # 清理過期時間戳
                    now = time.time()
                    self.request_timestamps = [
                        ts for ts in self.request_timestamps 
                        if now - ts < self.time_window
                    ]
            
            self.request_timestamps.append(time.time())


class APIErrorHandler:
    """API 錯誤處理器 with retry mechanism"""
    
    @staticmethod
    def retry_on_failure(max_retries: int = 3, delay: float = 2.0):
        """
        Decorator for retrying failed API calls with exponential backoff.
        
        Args:
            max_retries: Maximum number of retry attempts
            delay: Initial delay in seconds (doubles each retry)
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt < max_retries - 1:
                            wait_time = delay * (2 ** attempt)  # Exponential backoff
                            logging.warning(
                                f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                                f"Retrying in {wait_time}s..."
                            )
                            time.sleep(wait_time)
                        else:
                            logging.error(f"{func.__name__} failed after {max_retries} attempts: {e}", exc_info=True)
                            raise
                return None
            return wrapper
        return decorator


class FinMindClient:
    """
    FinMind API 客戶端封裝
    
    提供台股基本面數據抓取功能：
    - 財務報表 (損益表、資產負債表、現金流量表)
    - 月營收數據
    - 股票清單
    """
    
    def __init__(self, api_token: str = ""):
        """
        Initialize FinMind client.
        
        Args:
            api_token: FinMind API token (required for API access)
        """
        self.api_token = api_token
        self.data_loader = DataLoader()
        self.data_loader.login_by_token(api_token=api_token) if api_token else None
        self.rate_limiter = RateLimiter(max_requests=3, time_window=1.0)
        self.logger = logging.getLogger(__name__)
        self.logger.info("FinMind API client initialized")

    @APIErrorHandler.retry_on_failure(max_retries=3, delay=2.0)
    def get_stock_list(self, market: str = "all") -> pd.DataFrame:
        """
        獲取台股股票清單
        
        Args:
            market: 市場別 ('TSE'=上市, 'OTC'=上櫃, or 'all'=全部)
            
        Returns:
            DataFrame with columns: stock_id, stock_name, industry_category, type
            
        Raises:
            Exception: API request failed after retries
        """
        self.rate_limiter.wait_if_needed()
        
        try:
            df = self.data_loader.taiwan_stock_info()
            
            if df is None or df.empty:
                raise ValueError("Empty stock list returned from API")
            
            # FinMind uses 'type' column with values: 'twse' (上市) and 'tpex' (上櫃)
            # Filter by market if specified
            if market == "TSE":
                df = df[df['type'] == 'twse'].copy()
            elif market == "OTC":
                df = df[df['type'] == 'tpex'].copy()
            elif market != "all":
                raise ValueError(f"Invalid market: {market}. Must be 'TSE', 'OTC', or 'all'")
            
            # Get unique stocks (remove duplicates by stock_id)
            df = df.drop_duplicates(subset=['stock_id'], keep='last')
            
            self.logger.info(f"Retrieved {len(df)} stocks from market: {market}")
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to fetch stock list: {e}", exc_info=True)
            raise

    @APIErrorHandler.retry_on_failure(max_retries=3, delay=2.0)
    def get_financial_statements(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """
        獲取財務報表數據 (季報)
        
        Args:
            symbol: 股票代碼 (e.g., '2330')
            start_date: 開始日期 (format: '2024-01-01')
            end_date: 結束日期 (format: '2024-12-31')
            
        Returns:
            DataFrame with financial statement data including:
            - date: 財報日期
            - revenue: 營業收入
            - operating_income: 營業利益
            - net_income: 稅後淨利
            - gross_profit: 毛利
            - operating_expense: 營業費用
            
        Raises:
            ValueError: Invalid date format or empty result
            Exception: API request failed
        """
        self.rate_limiter.wait_if_needed()
        
        try:
            df = self.data_loader.taiwan_stock_financial_statement(
                stock_id=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                self.logger.warning(f"No financial statement data for {symbol} ({start_date} to {end_date})")
                return pd.DataFrame()
            
            # Ensure date column is datetime
            if 'date' in df.columns:
                df['date'] = df['date'].astype(str)
            
            self.logger.debug(f"Retrieved {len(df)} financial records for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to fetch financial statements for {symbol}: {e}", exc_info=True)
            raise

    @APIErrorHandler.retry_on_failure(max_retries=3, delay=2.0)
    def get_balance_sheet(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """
        獲取資產負債表數據
        
        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            DataFrame with balance sheet data including:
            - date: 財報日期
            - total_assets: 總資產
            - total_liabilities: 總負債
            - equity: 股東權益
            
        Raises:
            Exception: API request failed
        """
        self.rate_limiter.wait_if_needed()
        
        try:
            df = self.data_loader.taiwan_stock_balance_sheet(
                stock_id=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                self.logger.warning(f"No balance sheet data for {symbol}")
                return pd.DataFrame()
            
            if 'date' in df.columns:
                df['date'] = df['date'].astype(str)
            
            self.logger.debug(f"Retrieved {len(df)} balance sheet records for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to fetch balance sheet for {symbol}: {e}", exc_info=True)
            raise

    @APIErrorHandler.retry_on_failure(max_retries=3, delay=2.0)
    def get_cash_flow(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """
        獲取現金流量表數據
        
        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            DataFrame with cash flow data including:
            - date: 財報日期
            - operating_cash_flow: 營業現金流
            - investing_cash_flow: 投資現金流
            - financing_cash_flow: 融資現金流
            
        Raises:
            Exception: API request failed
        """
        self.rate_limiter.wait_if_needed()
        
        try:
            df = self.data_loader.taiwan_stock_cash_flows_statement(
                stock_id=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                self.logger.warning(f"No cash flow data for {symbol}")
                return pd.DataFrame()
            
            if 'date' in df.columns:
                df['date'] = df['date'].astype(str)
            
            self.logger.debug(f"Retrieved {len(df)} cash flow records for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to fetch cash flow for {symbol}: {e}", exc_info=True)
            raise

    @APIErrorHandler.retry_on_failure(max_retries=3, delay=2.0)
    def get_monthly_revenue(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """
        獲取月營收數據
        
        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            DataFrame with monthly revenue data including:
            - date: 年月
            - revenue: 當月營收
            - revenue_yoy: 營收年增率 (%)
            
        Raises:
            Exception: API request failed
        """
        self.rate_limiter.wait_if_needed()
        
        try:
            df = self.data_loader.taiwan_stock_month_revenue(
                stock_id=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                self.logger.warning(f"No monthly revenue data for {symbol}")
                return pd.DataFrame()
            
            if 'date' in df.columns:
                df['date'] = df['date'].astype(str)
            
            self.logger.debug(f"Retrieved {len(df)} monthly revenue records for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to fetch monthly revenue for {symbol}: {e}", exc_info=True)
            raise

    @APIErrorHandler.retry_on_failure(max_retries=3, delay=2.0)
    def get_daily_price(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """獲取每日股價數據 (OHLCV)"""
        self.rate_limiter.wait_if_needed()
        try:
            df = self.data_loader.taiwan_stock_daily(
                stock_id=symbol,
                start_date=start_date,
                end_date=end_date
            )
            if df is None or df.empty:
                return pd.DataFrame()
            if 'date' in df.columns:
                df['date'] = df['date'].astype(str)
            return df
        except KeyError as e:
            if str(e) == "'data'":
                self.logger.warning(f"No price data available for {symbol}")
                return pd.DataFrame()
            raise
        except Exception as e:
            self.logger.error(f"Failed to fetch daily price for {symbol}: {e}", exc_info=True)
            raise

    @APIErrorHandler.retry_on_failure(max_retries=3, delay=2.0)
    def get_institutional_investors(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """獲取三大法人買賣超數據"""
        self.rate_limiter.wait_if_needed()
        try:
            df = self.data_loader.taiwan_stock_institutional_investors(
                stock_id=symbol,
                start_date=start_date,
                end_date=end_date
            )
            if df is None or df.empty:
                return pd.DataFrame()
            if 'date' in df.columns:
                df['date'] = df['date'].astype(str)
            return df
        except KeyError as e:
            if str(e) == "'data'":
                self.logger.warning(f"No institutional data available for {symbol}")
                return pd.DataFrame()
            raise
        except Exception as e:
            self.logger.error(f"Failed to fetch institutional data for {symbol}: {e}", exc_info=True)
            raise

    @APIErrorHandler.retry_on_failure(max_retries=3, delay=2.0)
    def get_shareholding(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """獲取大戶持股數據 (每週)"""
        self.rate_limiter.wait_if_needed()
        try:
            # 使用正確的每週細分持股數據集
            df = self.data_loader.taiwan_stock_holding_shares_per(
                stock_id=symbol,
                start_date=start_date,
                end_date=end_date
            )
            if df is None or df.empty:
                return pd.DataFrame()
            if 'date' in df.columns:
                df['date'] = df['date'].astype(str)
            return df
        except KeyError as e:
            if str(e) == "'data'":
                self.logger.warning(f"No holding shares data available for {symbol}")
                return pd.DataFrame()
            return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Failed to fetch holding shares per for {symbol}: {e}", exc_info=True)
            return pd.DataFrame() # 非關鍵錯誤，返回空

    def get_comprehensive_fundamentals(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """
        獲取完整基本面數據（一次抓取所有報表）
        
        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            Dictionary containing:
            - 'financial_statement': 損益表
            - 'balance_sheet': 資產負債表
            - 'cash_flow': 現金流量表
            - 'monthly_revenue': 月營收
            
        Raises:
            Exception: API request failed
        """
        self.logger.info(f"Fetching comprehensive fundamentals for {symbol} ({start_date} to {end_date})")
        
        result = {
            'financial_statement': self.get_financial_statements(symbol, start_date, end_date),
            'balance_sheet': self.get_balance_sheet(symbol, start_date, end_date),
            'cash_flow': self.get_cash_flow(symbol, start_date, end_date),
            'monthly_revenue': self.get_monthly_revenue(symbol, start_date, end_date)
        }
        
        return result


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    print("FinMindClient module loaded successfully")
