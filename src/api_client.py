"""
Shioaji API 客戶端模組

提供永豐金 Shioaji API 的封裝，實現：
- Singleton 模式確保連線唯一性
- Context Manager 自動管理連線生命週期
- 速率限制與錯誤重試機制
- 歷史數據、法人買賣超等數據抓取

參考：docs/Implementation.md 第 3.1 節
"""

import threading
import time
import logging
from typing import Optional, List
import pandas as pd
import shioaji as sj
from datetime import datetime
from src.utils.exceptions import APIConnectionError

class RateLimiter:
    """
    API 請求速率限制器
    """
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_timestamps = []
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """若超過速率限制則等待"""
        with self.lock:
            now = time.time()
            # 清理超時的時間戳
            self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < self.time_window]
            
            if len(self.request_timestamps) >= self.max_requests:
                sleep_time = self.time_window - (now - self.request_timestamps[0])
                if sleep_time > 0:
                    logging.warning(f"超過速率限制，等待 {sleep_time:.2f} 秒...")
                    time.sleep(sleep_time)
            
            self.request_timestamps.append(time.time())

class APIErrorHandler:
    """API 錯誤處理器"""
    @staticmethod
    def retry_on_failure(max_retries=3, delay=5):
        def decorator(func):
            def wrapper(*args, **kwargs):
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logging.warning(f"{func.__name__} 失敗 (第 {attempt + 1} 次): {e}")
                            time.sleep(delay * (attempt + 1))
                        else:
                            logging.error(f"{func.__name__} 最終失敗: {e}", exc_info=True)
                            raise
                return None
            return wrapper
        return decorator

class ShioajiClient:
    """
    Shioaji API 客戶端封裝
    Singleton + Context Manager
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, api_key: str = "", secret_key: str = "", simulation: bool = False):
        if not hasattr(self, 'initialized'):
            self.api_key = api_key
            self.secret_key = secret_key
            self.simulation = simulation
            self.api = sj.Shioaji(simulation=simulation)
            self.is_connected = False
            self.lock = threading.Lock()
            self.rate_limiter = RateLimiter(max_requests=50, time_window=60) # 略低於官方限制以保安全
            self.initialized = True
            self.logger = logging.getLogger(__name__)

    def connect(self) -> bool:
        with self.lock:
            if self.is_connected:
                return True
            try:
                self.api.login(api_key=self.api_key, secret_key=self.secret_key)
                self.is_connected = True
                self.logger.info(f"Shioaji API {'模擬' if self.simulation else '正式'}環境連線成功")
                return True
            except Exception as e:
                self.logger.error(f"Shioaji API 登入失敗: {e}", exc_info=True)
                raise APIConnectionError(f"API 登入失敗: {e}")

    def disconnect(self):
        with self.lock:
            if self.is_connected:
                self.api.logout()
                self.is_connected = False
                self.logger.info("Shioaji API 已登出")

    @APIErrorHandler.retry_on_failure(max_retries=3)
    def get_historical_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        if not self.is_connected:
            self.connect()
        
        self.rate_limiter.wait_if_needed()
        
        try:
            contract = self.api.Contracts.Stocks[symbol]
            kbars = self.api.kbars(contract=contract, start=start_date, end=end_date)
            
            df = pd.DataFrame({
                'date': kbars.ts,
                'open': kbars.Open,
                'high': kbars.High,
                'low': kbars.Low,
                'close': kbars.Close,
                'volume': kbars.Volume,
                'amount': kbars.Amount
            })
            df['date'] = pd.to_datetime(df['date'])
            df['symbol'] = symbol
            return df
        except Exception as e:
            self.logger.error(f"抓取 {symbol} 歷史數據失敗: {e}", exc_info=True)
            raise

    @APIErrorHandler.retry_on_failure(max_retries=3)
    def get_institutional_trades(self, date_str: str) -> pd.DataFrame:
        # 注意：Shioaji 抓取法人數據可能需要特定權限或調用方式
        # 這裡實作一個 placeholder，具體取決於 SDK 版本
        if not self.is_connected:
            self.connect()
        
        self.rate_limiter.wait_if_needed()
        
        # 永豐金法人買賣超通常是從日行情快照中取得，或是有專門的 API
        # 這裡示意透過 snapshot 取得
        try:
            # 實際上法人數據在 Shioaji 中可能需要透過其他組件如 `api.credit_enquires` 
            # 或是透過與交易所同步的 CSV/API 處理。
            # 這裡暫時實作為空，待數據源確認
            self.logger.warning("get_institutional_trades 尚未完全實作（需確認數據源權限）")
            return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"抓取 {date_str} 法人數據失敗: {e}", exc_info=True)
            raise

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("ShioajiClient 模組已載入")

