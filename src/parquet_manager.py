"""
Parquet 數據管理器模組

提供統一的 Parquet 數據讀寫接口，實現：
- 時間分區與個股分區管理
- 數據讀寫與查詢優化
- 分區轉置（ETL 轉換）

參考：docs/Implementation.md 第 3.4.2 節
"""

import logging
import os
from pathlib import Path
from typing import Optional, List
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime
from src.utils.exceptions import DataNotFoundError

class ParquetManager:
    """
    Parquet 數據管理器 - 管理時間分區與個股分區

    設計模式：Repository Pattern (抽象數據訪問層)
    """

    def __init__(self, base_path: str = 'data'):
        self.base_path = Path(base_path)
        self.daily_path = self.base_path / 'daily'
        self.history_path = self.base_path / 'history'
        self.fundamentals_path = self.base_path / 'fundamentals'
        self.chips_path = self.base_path / 'chips'
        self.shareholding_path = self.base_path / 'shareholding'
        
        # 建立目錄
        self.daily_path.mkdir(parents=True, exist_ok=True)
        self.history_path.mkdir(parents=True, exist_ok=True)
        self.fundamentals_path.mkdir(parents=True, exist_ok=True)
        self.chips_path.mkdir(parents=True, exist_ok=True)
        self.shareholding_path.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)

    def write_time_partition(self, data: pd.DataFrame, partition_date: str):
        """寫入時間分區 /data/daily/date=YYYY-MM-DD/"""
        path = self.daily_path / f"date={partition_date}"
        path.mkdir(parents=True, exist_ok=True)
        
        file_path = path / "data.parquet"
        data.to_parquet(file_path, engine='pyarrow', compression='snappy', index=False)
        self.logger.info(f"成功寫入時間分區: {file_path}")

    def write_symbol_partition(self, data: pd.DataFrame, symbol: str):
        """寫入個股分區 /data/history/symbol=XXXX/"""
        path = self.history_path / f"symbol={symbol}"
        path.mkdir(parents=True, exist_ok=True)
        
        # Ensure 'date' column is string before writing
        if 'date' in data.columns:
            data['date'] = data['date'].astype(str)

        file_path = path / "data.parquet"
        data.to_parquet(file_path, engine='pyarrow', compression='snappy', index=False)
        self.logger.debug(f"成功寫入個股分區: {file_path}")

    def read_time_partition(self, start_date: str, end_date: str = None) -> pd.DataFrame:
        """讀取時間分區範圍數據"""
        if end_date is None:
            end_date = start_date
            
        dataset = pq.ParquetDataset(
            self.daily_path,
            filters=[('date', '>=', start_date), ('date', '<=', end_date)]
        )
        df = dataset.read().to_pandas()
        # Ensure 'date' column is string for consistency, though it should be if stored as such
        if 'date' in df.columns:
            df['date'] = df['date'].astype(str)
        return df

    def read_symbol_partition(self, symbol: str) -> pd.DataFrame:
        """讀取個股分區數據"""
        file_path = self.history_path / f"symbol={symbol}" / "data.parquet"
        if not file_path.exists():
            self.logger.warning(f"找不到股個分區數據: {symbol}")
            return pd.DataFrame()
        df = pd.read_parquet(file_path)
        
        # 標準化欄位名稱 (處理 FinMind 不同資料源的差異)
        column_mapping = {
            'max': 'high',
            'min': 'low',
            'Trading_Volume': 'volume',
            'Trading_money': 'amount'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        # Ensure 'date' column is string for consistency
        if 'date' in df.columns:
            df['date'] = df['date'].astype(str)
        return df

    def transpose_to_symbol_partition(self, date_str: str):
        """將時間分區轉置為個股分區 (ETL)"""
        self.logger.info(f"開始轉置 {date_str} 的數據至個股分區...")
        
        # 1. 讀取該日的每日數據
        daily_file = self.daily_path / f"date={date_str}" / "data.parquet"
        if not daily_file.exists():
            self.logger.error(f"找不到每日數據檔案: {daily_file}", exc_info=True)
            return
            
        daily_df = pd.read_parquet(daily_file)
        
        # 2. 按股票代碼遍歷並附加到個股檔案
        for symbol, group in daily_df.groupby('symbol'):
            self._append_to_history(symbol, group)
            
        self.logger.info(f"轉置完成: {date_str}")

    def _append_to_history(self, symbol: str, new_data: pd.DataFrame):
        """輔助函數：將新數據附加到個股歷史檔案並去重"""
        path = self.history_path / f"symbol={symbol}"
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / "data.parquet"
        
        if file_path.exists():
            history_df = pd.read_parquet(file_path)
            # 合併並去重
            combined_df = pd.concat([history_df, new_data]).drop_duplicates(subset=['date'], keep='last')
            combined_df = combined_df.sort_values('date')
        else:
            combined_df = new_data.sort_values('date')
            
        combined_df.to_parquet(file_path, engine='pyarrow', compression='snappy', index=False)

    def write_fundamental_data(self, df: pd.DataFrame, symbol: str):
        """將基本面數據寫入個股分區"""
        path = self.fundamentals_path / f"symbol={symbol}"
        path.mkdir(parents=True, exist_ok=True)
        
        # 確保日期為字串
        if 'date' in df.columns:
            df['date'] = df['date'].astype(str)
            
        file_path = path / "data.parquet"
        df.to_parquet(file_path, index=False)
        self.logger.debug(f"成功寫入個股基本面數據: {file_path}")

    def read_fundamental_data(self, symbol: str) -> pd.DataFrame:
        """讀取財務報表數據"""
        file_path = self.fundamentals_path / f"symbol={symbol}" / "data.parquet"
        if not file_path.exists():
            self.logger.warning(f"找不到財務數據: {symbol}")
            return pd.DataFrame()
        return pd.read_parquet(file_path)

    def write_chip_data(self, symbol: str, data: pd.DataFrame):
        """寫入籌碼數據 (三大法人買賣超) - 支援附加與去重"""
        path = self.chips_path / f"symbol={symbol}"
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / "data.parquet"
        
        if file_path.exists():
            history_df = pd.read_parquet(file_path)
            # Ensure consistent type for merging
            history_df['date'] = history_df['date'].astype(str)
            data['date'] = data['date'].astype(str)
            
            combined_df = pd.concat([history_df, data]).drop_duplicates(subset=['date'], keep='last')
            combined_df = combined_df.sort_values('date')
        else:
            data['date'] = data['date'].astype(str)
            combined_df = data.sort_values('date')
            
        combined_df.to_parquet(file_path, engine='pyarrow', compression='snappy', index=False)

    def read_chip_data(self, symbol: str) -> pd.DataFrame:
        """讀取籌碼數據"""
        file_path = self.chips_path / f"symbol={symbol}" / "data.parquet"
        if not file_path.exists():
            return pd.DataFrame()
        return pd.read_parquet(file_path)

    def write_shareholding_data(self, symbol: str, data: pd.DataFrame):
        """寫入大戶持股數據 - 支援附加與去重"""
        path = self.shareholding_path / f"symbol={symbol}"
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / "data.parquet"
        
        if file_path.exists():
            history_df = pd.read_parquet(file_path)
            combined_df = pd.concat([history_df, data]).drop_duplicates(subset=['date'], keep='last')
            combined_df = combined_df.sort_values('date')
        else:
            combined_df = data.sort_values('date')
            
        combined_df.to_parquet(file_path, engine='pyarrow', compression='snappy', index=False)


    def read_shareholding_data(self, symbol: str) -> pd.DataFrame:
        """讀取大戶持股數據"""
        file_path = self.shareholding_path / f"symbol={symbol}" / "data.parquet"
        if not file_path.exists():
            return pd.DataFrame()
        return pd.read_parquet(file_path)

    def cleanup_old_data(self, keep_days: int = 30):
        """清理舊的時間分區數據"""
        # 這裡實作簡單的目錄刪除邏輯
        self.logger.info(f"清理 {keep_days} 天前的舊數據...")
        # TODO: 實作日期判斷與刪除
        pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("ParquetManager 模組已載入")

