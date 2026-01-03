"""
FinGear - 台股量化分析系統核心模組

本模組提供 FinGear 系統的所有核心功能，包括：
- API 客戶端（Shioaji 封裝）
- 數據管理器（Parquet 讀寫）
- 因子計算引擎（基本面、籌碼面、技術面）
- 選股篩選器（三層篩選邏輯）
- 數據驗證器（品質檢查）
- 通知服務（Line、Telegram）
"""

__version__ = "0.1.0"
__author__ = "FinGear Team"

# Optional imports - only load if dependencies are available
try:
    from .api_client import ShioajiClient
    _SHIOAJI_AVAILABLE = True
except ImportError:
    ShioajiClient = None
    _SHIOAJI_AVAILABLE = False

from .parquet_manager import ParquetManager
from .factors import FactorEngine
from .screener import StockScreener
from .data_validator import DataValidator
from .notification import NotificationService

__all__ = [
    "ShioajiClient",
    "ParquetManager",
    "FactorEngine",
    "StockScreener",
    "DataValidator",
    "NotificationService",
]
