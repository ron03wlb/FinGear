"""
pytest 配置與共用 fixtures

參考：Requirement/Implementation.md 第 5.1 節
"""

import pytest
import pandas as pd
from unittest.mock import Mock


@pytest.fixture
def mock_data_manager():
    """Mock 數據管理器"""
    manager = Mock()

    # 模擬財報數據
    manager.read_parquet.return_value = pd.DataFrame({
        'date': pd.date_range('2023-01-01', periods=8, freq='QE'),
        'net_income': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700],
        'equity': [5000, 5200, 5400, 5600, 5800, 6000, 6200, 6400],
        'eps': [2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4]
    })

    return manager


@pytest.fixture
def sample_price_data():
    """範例價格數據"""
    return pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=100),
        'open': [100 + i for i in range(100)],
        'high': [105 + i for i in range(100)],
        'low': [95 + i for i in range(100)],
        'close': [100 + i for i in range(100)],
        'volume': [1000000 for _ in range(100)]
    })
