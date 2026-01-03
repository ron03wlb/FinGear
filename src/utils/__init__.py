"""
通用工具函數模組

提供共用的輔助函數，包括：
- 日期處理工具
- 資料轉換工具
- 日誌配置工具
"""

import logging
from datetime import datetime, timedelta
from typing import List
import pandas as pd


def get_trading_days(start_date: str, end_date: str) -> List[str]:
    """取得交易日列表 (簡單版: 排除週末)"""
    dates = pd.date_range(start=start_date, end=end_date)
    return [d.strftime("%Y-%m-%d") for d in dates if d.dayofweek < 5]

def setup_logging(log_level: str = 'INFO'):
    """配置基本日誌"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def load_config(config_path: str) -> dict:
    """載入 JSON 配置"""
    import json
    with open(config_path, 'r') as f:
        return json.load(f)



if __name__ == '__main__':
    print("Utils 模組已載入")
