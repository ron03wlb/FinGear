"""
FactorEngine 單元測試

參考：Requirement/Implementation.md 第 5.1.2 節
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from src.factors import FactorEngine


class TestFactorEngine:
    """FactorEngine 單元測試"""

    @pytest.fixture
    def factor_engine(self, mock_data_manager):
        """初始化因子引擎"""
        return FactorEngine(data_manager=mock_data_manager)

    def test_calculate_roe_正常情況(self, factor_engine):
        """測試 ROE 計算 - 正常情況"""
        # TODO: 實作測試邏輯
        pass

    def test_calculate_eps_yoy_正成長(self, factor_engine):
        """測試 EPS YoY 計算 - 正成長"""
        # TODO: 實作測試邏輯
        pass

    def test_score_factor_ROE評分(self, factor_engine):
        """測試因子評分邏輯 - ROE"""
        # TODO: 實作測試邏輯
        pass
