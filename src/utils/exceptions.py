"""
自定義異常模組

定義系統中使用的自定義異常類別，用於精確的錯誤處理與日誌記錄。
"""

class FinGearError(Exception):
    """FinGear 基礎異常"""
    pass

class DataNotFoundError(FinGearError):
    """當找不到 Parquet 分區或數據時拋出"""
    pass

class DataCorruptionError(FinGearError):
    """當 Parquet 文件損壞或無效時拋出"""
    pass

class APIConnectionError(FinGearError):
    """當 Shioaji API 或其他外部服務連線失敗時拋出"""
    pass

class RateLimitExceeded(FinGearError):
    """當超過 API 速率限制時拋出"""
    pass

class ValidationError(FinGearError):
    """當數據模式 (Schema) 或內容驗證失敗時拋出"""
    pass
