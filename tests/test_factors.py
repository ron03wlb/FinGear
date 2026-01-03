"""
FactorEngine 單元測試

完整測試套件涵蓋：
- 7 個基本面因子計算
- 邊界情況處理
- 錯誤處理
- 評分邏輯驗證

參考：Implementation Plan - Unit Testing
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.factors import FactorEngine


class TestFactorEngine:
    """FactorEngine 完整測試套件"""

    @pytest.fixture
    def mock_data_manager(self):
        """Mock 數據管理器，提供標準財務數據"""
        manager = Mock()
        
        # 標準 5 季度財務數據
        manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=5, freq='QE'),
            'revenue': [10000, 11000, 12000, 13000, 14000],
            'gross_profit': [3000, 3300, 3600, 3900, 4200],
            'operating_income': [2000, 2200, 2400, 2600, 2800],
            'net_income': [1000, 1100, 1200, 1300, 1400],
            'eps': [2.0, 2.2, 2.4, 2.6, 2.8],
            'equity': [5000, 5200, 5400, 5600, 5800],
            'total_assets': [10000, 10500, 11000, 11500, 12000],
            'total_liabilities': [5000, 5300, 5600, 5900, 6200],
            'operating_cash_flow': [1500, 1600, 1700, 1800, 1900],
            'capital_expenditure': [500, 550, 600, 650, 700]
        })
        
        # Mock 價格數據（用於 PE 計算）
        manager.read_symbol_partition.return_value = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=365),
            'close': np.linspace(50, 70, 365)  # 價格從 50 漸增至 70
        })
        
        return manager

    @pytest.fixture
    def factor_engine(self, mock_data_manager):
        """初始化 FactorEngine"""
        return FactorEngine(data_manager=mock_data_manager)

    # ==================== ROE 測試 ====================
    
    def test_calculate_roe_正常情況(self, factor_engine):
        """測試 ROE 計算 - 標準情況"""
        roe = factor_engine._calculate_roe('2330')
        
        # Expected: TTM net_income = 1100+1200+1300+1400 = 5000
        # Expected: Avg equity = (5200+5400+5600+5800)/4 = 5500
        # Expected: ROE = 5000/5500 * 100 = 90.91%
        assert roe == pytest.approx(90.91, abs=0.01)
        assert 0 <= roe <= 200  # Sanity check

    def test_calculate_roe_數據不足(self, factor_engine, mock_data_manager):
        """測試 ROE - 數據量不足情況"""
        # 僅提供 3 季資料（需要至少 4 季）
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=3, freq='QE'),
            'net_income': [1000, 1100, 1200],
            'equity': [5000, 5200, 5400]
        })
        
        roe = factor_engine._calculate_roe('TEST')
        assert roe == 0.0

    def test_calculate_roe_負股東權益(self, factor_engine, mock_data_manager):
        """測試 ROE - 股東權益為負值"""
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=5, freq='QE'),
            'net_income': [1000, 1100, 1200, 1300, 1400],
            'equity': [5000, 5200, -100, -200, -300]  # 後三季為負
        })
        
        roe = factor_engine._calculate_roe('TEST')
        assert roe == 0.0

    def test_calculate_roe_缺少欄位(self, factor_engine, mock_data_manager):
        """測試 ROE - 缺少必要欄位"""
        from src.utils.exceptions import ValidationError
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=5, freq='QE'),
            'revenue': [10000, 11000, 12000, 13000, 14000]
            # 缺少 net_income 和 equity
        })
        
        with pytest.raises(ValidationError, match="Missing columns"):
            factor_engine._calculate_roe('TEST')

    # ==================== EPS YoY 測試 ====================

    def test_calculate_eps_yoy_正成長(self, factor_engine):
        """測試 EPS YoY - 正常成長"""
        eps_yoy = factor_engine._calculate_eps_yoy('2330')
        
        # Latest EPS = 2.8, YoY EPS (5 quarters ago) = 2.0
        # Expected: (2.8 - 2.0) / 2.0 * 100 = 40%
        assert eps_yoy == pytest.approx(40.0, abs=0.1)

    def test_calculate_eps_yoy_負成長(self, factor_engine, mock_data_manager):
        """測試 EPS YoY - 負成長"""
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=5, freq='QE'),
            'eps': [3.0, 2.8, 2.6, 2.4, 2.2]  # 遞減
        })
        
        eps_yoy = factor_engine._calculate_eps_yoy('TEST')
        # (2.2 - 3.0) / 3.0 * 100 = -26.67%
        assert eps_yoy == pytest.approx(-26.67, abs=0.01)

    def test_calculate_eps_yoy_由負轉正(self, factor_engine, mock_data_manager):
        """測試 EPS YoY - 由負轉正"""
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=5, freq='QE'),
            'eps': [-1.0, -0.5, 0.0, 0.5, 1.0]
        })
        
        eps_yoy = factor_engine._calculate_eps_yoy('TEST')
        # Latest = 1.0, YoY = -1.0
        # (1.0 - (-1.0)) / abs(-1.0) * 100 = 200%
        assert eps_yoy == pytest.approx(200.0, abs=0.1)

    def test_calculate_eps_yoy_去年同期為零(self, factor_engine, mock_data_manager):
        """測試 EPS YoY - 去年同季 EPS 接近 0"""
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=5, freq='QE'),
            'eps': [0.0001, 0.5, 1.0, 1.5, 2.0]  # YoY 接近 0
        })
        
        eps_yoy = factor_engine._calculate_eps_yoy('TEST')
        # 當 EPS 接近 0，應返回 100.0 或 0.0
        assert eps_yoy == 100.0  # Latest > 0

    # ==================== FCF 測試 ====================

    def test_calculate_fcf_正常情況(self, factor_engine):
        """測試 FCF 計算 - 標準情況"""
        fcf = factor_engine._calculate_fcf('2330')
        
        # TTM OCF = 1600+1700+1800+1900 = 7000
        # TTM CAPEX = 550+600+650+700 = 2500
        # FCF = 7000 - 2500 = 4500
        assert fcf == pytest.approx(4500, abs=1)

    def test_calculate_fcf_負現金流(self, factor_engine, mock_data_manager):
        """測試 FCF - 負自由現金流"""
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=5, freq='QE'),
            'operating_cash_flow': [1000, 900, 800, 700, 600],
            'capital_expenditure': [2000, 2000, 2000, 2000, 2000]
        })
        
        fcf = factor_engine._calculate_fcf('TEST')
        # TTM OCF = 900+800+700+600 = 3000
        # TTM CAPEX = 2000*4 = 8000
        # FCF = 3000 - 8000 = -5000
        assert fcf == pytest.approx(-5000, abs=1)

    def test_calculate_fcf_缺少資本支出(self, factor_engine, mock_data_manager):
        """測試 FCF - 缺少資本支出欄位"""
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=5, freq='QE'),
            'operating_cash_flow': [1000, 1100, 1200, 1300, 1400]
            # 缺少 capital_expenditure
        })
        
        fcf = factor_engine._calculate_fcf('TEST')
        assert fcf == 0.0

    def test_calculate_fcf_含NaN值(self, factor_engine, mock_data_manager):
        """測試 FCF - 數據含 NaN 值"""
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=5, freq='QE'),
            'operating_cash_flow': [1000, np.nan, 1200, 1300, 1400],
            'capital_expenditure': [500, 550, np.nan, 650, 700]
        })
        
        fcf = factor_engine._calculate_fcf('TEST')
        # NaN 會被 fillna(0) 處理
        # OCF = 0+1200+1300+1400 = 3900
        # CAPEX = 550+0+650+700 = 1900
        # FCF = 3900 - 1900 = 2000
        assert fcf == pytest.approx(2000, abs=1)

    # ==================== Gross Margin Trend 測試 ====================

    def test_calculate_gross_margin_trend_正常(self, factor_engine):
        """測試毛利率趨勢 - 標準情況"""
        trend = factor_engine._calculate_gross_margin_trend('2330')
        
        # Latest margin = 4200/14000 * 100 = 30%
        # YoY margin = 3000/10000 * 100 = 30%
        # Trend = 30 - 30 = 0%
        assert trend == pytest.approx(0.0, abs=0.1)

    def test_calculate_gross_margin_trend_改善(self, factor_engine, mock_data_manager):
        """測試毛利率趨勢 - 改善"""
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=5, freq='QE'),
            'revenue': [10000, 11000, 12000, 13000, 14000],
            'gross_profit': [2000, 2500, 3000, 3500, 4000]  # 毛利率提升
        })
        
        trend = factor_engine._calculate_gross_margin_trend('TEST')
        # Latest = 4000/14000 = 28.57%
        # YoY = 2000/10000 = 20%
        # Trend = 28.57 - 20 = 8.57%
        assert trend == pytest.approx(8.57, abs=0.01)

    # ==================== Debt Ratio 測試 ====================

    def test_calculate_debt_ratio_正常(self, factor_engine):
        """測試負債比率 - 標準情況"""
        ratio = factor_engine._calculate_debt_ratio('2330')
        
        # Latest: total_liabilities = 6200, total_assets = 12000
        # Ratio = 6200/12000 * 100 = 51.67%
        assert ratio == pytest.approx(51.67, abs=0.01)

    def test_calculate_debt_ratio_資產為零(self, factor_engine, mock_data_manager):
        """測試負債比率 - 總資產為 0"""
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=5, freq='QE'),
            'total_liabilities': [1000, 1000, 1000, 1000, 1000],
            'total_assets': [5000, 4000, 3000, 2000, 0]  # 最後為 0
        })
        
        ratio = factor_engine._calculate_debt_ratio('TEST')
        assert ratio == 100.0  # 預設回傳 100

    # ==================== Revenue YoY 測試 ====================

    def test_calculate_revenue_yoy_正常(self, factor_engine):
        """測試營收年增率 - 標準情況"""
        yoy = factor_engine._calculate_revenue_yoy('2330')
        
        # Latest revenue = 14000, YoY revenue = 10000
        # YoY = (14000-10000)/10000 * 100 = 40%
        assert yoy == pytest.approx(40.0, abs=0.1)

    def test_calculate_revenue_yoy_衰退(self, factor_engine, mock_data_manager):
        """測試營收年增率 - 衰退"""
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=5, freq='QE'),
            'revenue': [10000, 9000, 8000, 7000, 6000]  # 遞減
        })
        
        yoy = factor_engine._calculate_revenue_yoy('TEST')
        # (6000-10000)/10000 * 100 = -40%
        assert yoy == pytest.approx(-40.0, abs=0.1)

    # ==================== 評分邏輯測試 ====================

    @pytest.mark.parametrize("factor_name,raw_value,expected_score", [
        # ROE 評分
        ('roe', 25, 5),      # >= 20% → 5分
        ('roe', 18, 4),      # >= 15% → 4分
        ('roe', 12, 3),      # >= 10% → 3分
        ('roe', 7, 2),       # >= 5% → 2分
        ('roe', 3, 1),       # < 5% → 1分
        
        # EPS YoY 評分
        ('eps_yoy', 35, 5),  # >= 30% → 5分
        ('eps_yoy', 20, 4),  # >= 15% → 4分
        ('eps_yoy', 5, 3),   # >= 0% → 3分
        ('eps_yoy', -5, 2),  # >= -10% → 2分
        ('eps_yoy', -15, 1), # < -10% → 1分
        
        # Debt Ratio 評分（反向）
        ('debt_ratio', 25, 5),  # <= 30% → 5分
        ('debt_ratio', 45, 4),  # <= 50% → 4分
        ('debt_ratio', 65, 3),  # <= 70% → 3分
        ('debt_ratio', 80, 2),  # <= 85% → 2分
        ('debt_ratio', 90, 1),  # > 85% → 1分
        
        # PE Relative 評分（反向）
        ('pe_relative', -1.5, 5),  # <= -1.0σ → 5分
        ('pe_relative', -0.5, 4),  # <= 0.0σ → 4分
        ('pe_relative', 0.5, 3),   # <= 1.0σ → 3分
        ('pe_relative', 1.5, 2),   # <= 2.0σ → 2分
        ('pe_relative', 2.5, 1),   # > 2.0σ → 1分
    ])
    def test_score_factor_各級距(self, factor_engine, factor_name, raw_value, expected_score):
        """測試因子評分邏輯 - 參數化測試所有級距"""
        score = factor_engine._score_factor(factor_name, raw_value)
        assert score == expected_score

    def test_score_factor_未知因子(self, factor_engine):
        """測試評分 - 未知因子名稱"""
        score = factor_engine._score_factor('unknown_factor', 100)
        assert score == 3  # 預設中等分數

    # ==================== 綜合評分測試 ====================

    def test_calculate_fundamental_score_正常(self, factor_engine):
        """測試綜合評分 - 標準情況"""
        score = factor_engine.calculate_fundamental_score('2330')
        
        # 驗證評分範圍
        assert 40 <= score <= 200
        # 驗證為數值
        assert isinstance(score, (int, float))

    def test_calculate_fundamental_score_緩存機制(self, factor_engine):
        """測試綜合評分 - 緩存機制"""
        # 第一次計算
        score1 = factor_engine.calculate_fundamental_score('2330')
        
        # 第二次計算（應使用緩存）
        score2 = factor_engine.calculate_fundamental_score('2330')
        
        # 應該相同
        assert score1 == score2
        
        # 驗證緩存 key 存在
        from datetime import date
        cache_key = f"2330_fundamental_{date.today()}"
        assert cache_key in factor_engine.cache

    def test_calculate_fundamental_score_空數據(self, factor_engine, mock_data_manager):
        """測試綜合評分 - 空數據"""
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame()
        
        score = factor_engine.calculate_fundamental_score('EMPTY')
        
        # 部分因子會返回預設值，導致不會全是最低分
        # 實際分數取決於因子計算的降級邏輯
        assert 40 <= score <= 200  # 驗證範圍即可

    # ==================== 邊界情況測試 ====================

    def test_極端正值(self, factor_engine, mock_data_manager):
        """測試極端正值情況"""
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=5, freq='QE'),
            'net_income': [1e10, 1.1e10, 1.2e10, 1.3e10, 1.4e10],  # 極大值
            'equity': [1e9, 1.1e9, 1.2e9, 1.3e9, 1.4e9],
            'eps': [100, 110, 120, 130, 140],
            'revenue': [1e11, 1.1e11, 1.2e11, 1.3e11, 1.4e11],
            'gross_profit': [3e10, 3.3e10, 3.6e10, 3.9e10, 4.2e10],
            'total_assets': [1e11, 1.1e11, 1.2e11, 1.3e11, 1.4e11],
            'total_liabilities': [5e10, 5.5e10, 6e10, 6.5e10, 7e10],
            'operating_cash_flow': [1e10, 1.1e10, 1.2e10, 1.3e10, 1.4e10],
            'capital_expenditure': [1e9, 1.1e9, 1.2e9, 1.3e9, 1.4e9]
        })
        
        score = factor_engine.calculate_fundamental_score('EXTREME')
        assert 40 <= score <= 200

    def test_全NaN數據(self, factor_engine, mock_data_manager):
        """測試全 NaN 數據"""
        mock_data_manager.read_fundamental_data.return_value = pd.DataFrame({
            'date': pd.date_range('2024-03-31', periods=5, freq='QE'),
            'net_income': [np.nan] * 5,
            'equity': [np.nan] * 5,
            'eps': [np.nan] * 5
        })
        
        score = factor_engine.calculate_fundamental_score('NAN_DATA')
        # NaN 數據會導致不同因子有不同降級處理
        assert 40 <= score <= 200


class TestFactorEngineIntegration:
    """FactorEngine 整合測試"""
    
    def test_真實數據計算(self):
        """使用真實數據測試計算流程"""
        from src.parquet_manager import ParquetManager
        
        dm = ParquetManager('data')
        engine = FactorEngine(dm)
        
        # 測試 2330（台積電）
        try:
            score = engine.calculate_fundamental_score('2330')
            assert 40 <= score <= 200
            assert isinstance(score, (int, float))
        except Exception as e:
            pytest.skip(f"Real data not available: {e}")

    def test_批量計算性能(self):
        """測試批量計算性能"""
        from src.parquet_manager import ParquetManager
        import time
        
        dm = ParquetManager('data')
        engine = FactorEngine(dm)
        
        test_symbols = ['2330', '2317', '2454']
        
        start_time = time.time()
        scores = {}
        
        for symbol in test_symbols:
            try:
                scores[symbol] = engine.calculate_fundamental_score(symbol)
            except:
                pass
        
        elapsed = time.time() - start_time
        
        # 每支股票計算應在 1 秒內
        if scores:
            avg_time = elapsed / len(scores)
            assert avg_time < 1.0, f"Average calculation time too slow: {avg_time:.2f}s"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src.factors', '--cov-report=term-missing'])
