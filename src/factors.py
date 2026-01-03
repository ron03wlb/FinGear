"""
因子計算引擎模組

提供基本面、籌碼面、技術面因子計算，實現：
- 7 因子綜合評分（ROE、EPS YoY、FCF 等）
- 因子緩存機制
- 評分規則引擎

參考：docs/Implementation.md 第 3.2 節
"""

import logging
import yaml
from datetime import date
from typing import Dict
from pathlib import Path
import pandas as pd
from src.utils.exceptions import ValidationError


class FactorEngine:
    """
    因子計算引擎

    職責：計算所有基本面、籌碼面、技術面因子
    設計模式：Strategy Pattern（不同因子策略可插拔）

    Attributes:
        data_manager: 數據管理器
        cache (dict): 因子緩存

    Examples:
        >>> engine = FactorEngine(data_manager)
        >>> score = engine.calculate_fundamental_score('2330')
    """

    def __init__(self, data_manager):
        """
        初始化因子引擎

        Args:
            data_manager: 數據管理器
        """
        self.data_manager = data_manager
        self.cache = {}
        self.logger = logging.getLogger(__name__)
        
        # 載入配置權重
        self.weights = self._load_weights()

        # 註冊因子計算策略
        self.fundamental_factors = {
            'roe': self._calculate_roe,
            'gross_margin_trend': self._calculate_gross_margin_trend,
            'debt_ratio': self._calculate_debt_ratio,
            'fcf': self._calculate_fcf,
            'revenue_yoy': self._calculate_revenue_yoy,
            'eps_yoy': self._calculate_eps_yoy,
            'pe_relative': self._calculate_pe_relative
        }

    def _load_weights(self) -> Dict[str, float]:
        """從 parameters.yaml 載入權重設定"""
        default_weights = {
            'roe': 0.20,
            'eps_yoy': 0.20,
            'fcf': 0.15,
            'gross_margin_trend': 0.15,
            'revenue_yoy': 0.10,
            'debt_ratio': 0.10,
            'pe_relative': 0.10
        }
        
        config_path = Path(__file__).parent.parent / 'config' / 'parameters.yaml'
        if not config_path.exists():
            self.logger.warning(f"找不到設定檔 {config_path}，使用預設權重")
            return default_weights
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                weights = config.get('screening', {}).get('factor_weights', {})
                if not weights:
                    return default_weights
                return weights
        except Exception as e:
            self.logger.error(f"讀取權重設定失敗: {e}，使用預設值")
            return default_weights

    def calculate_fundamental_score(self, symbol: str) -> float:
        """
        計算基本面綜合得分 (0-200 分)
        """
        # 1. 檢查緩存
        cache_key = f"{symbol}_fundamental_{date.today()}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # 2. 計算各因子分數
        scores = {}
        for factor_name, calc_func in self.fundamental_factors.items():
            try:
                raw_value = calc_func(symbol)
                scores[factor_name] = self._score_factor(factor_name, raw_value)
            except Exception as e:
                self.logger.warning(f"計算因子 {factor_name} 失敗 ({symbol}): {e}")
                scores[factor_name] = 1 # 預設最低分

        # 3. 加權聚合
        # 從設定檔讀取權重，若無則降級處理
        weights = self.weights
        
        weighted_score = sum(scores[f] * weights.get(f, 0) for f in scores if f in weights)
        # 1.0 (全最低) -> 40分, 5.0 (全最高) -> 200分
        final_score = weighted_score * 40

        # 4. 寫入緩存
        self.cache[cache_key] = final_score

        return final_score

    def _get_fundamental_data(self, symbol: str) -> pd.DataFrame:
        """
        從個股財務分區讀取數據
        
        優先使用真實 FinMind 數據，若無則返回空 DataFrame
        (可在上層邏輯中決定是否呼叫 mock 生成)
        """
        df = self.data_manager.read_fundamental_data(symbol)
        
        if df.empty:
            self.logger.debug(f"No fundamental data found for {symbol}")
            return pd.DataFrame()
        
        # Log data source
        if len(df) >= 5:
            self.logger.debug(f"Using real fundamental data for {symbol} ({len(df)} quarters)")
        else:
            self.logger.warning(
                f"Insufficient fundamental data for {symbol} (only {len(df)} quarters, need at least 5)"
            )
        
        # Ensure date column is datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
        
        return df

    def _calculate_roe(self, symbol: str) -> float:
        """
        計算 ROE (Return on Equity)
        
        ROE = 稅後淨利 (TTM) ÷ 平均股東權益 × 100%
        
        Args:
            symbol: 股票代碼
            
        Returns:
            ROE (百分比)
        """
        df = self._get_fundamental_data(symbol)
        required = {'net_income', 'equity'}
        
        # 數據驗證
        if df.empty or len(df) < 4:
            self.logger.debug(f"Insufficient data for ROE calculation: {symbol}")
            return 0.0
        
        # 檢查數據完整性
        if not required.issubset(df.columns):
            raise ValidationError(f"Missing columns for ROE: {required - set(df.columns)}")
        
        # 檢查股東權益是否有效
        if (df['equity'].tail(4) <= 0).any():
            self.logger.warning(f"{symbol}: Negative/zero equity detected")
            return 0.0
        
        # TTM 淨利: 最近四季加總
        ttm_net_income = df['net_income'].tail(4).sum()
        # 平均股東權益: 最近四季的平均值
        avg_equity = df['equity'].tail(4).mean()
        
        if avg_equity <= 0:
            return 0.0
            
        roe = (ttm_net_income / avg_equity) * 100
        self.logger.debug(f"{symbol} ROE: {roe:.2f}%")
        return roe

    def _calculate_eps_yoy(self, symbol: str) -> float:
        """EPS YoY = (本季 EPS - 去年同季 EPS) ÷ |去年同季 EPS| × 100%"""
        df = self._get_fundamental_data(symbol)
        if df.empty or 'eps' not in df.columns or len(df) < 5:
            return 0.0
        
        latest_eps = df.iloc[-1]['eps']
        yoy_eps = df.iloc[-5]['eps']
        
        if abs(yoy_eps) < 0.001:
            return 100.0 if latest_eps > 0 else 0.0
            
        return ((latest_eps - yoy_eps) / abs(yoy_eps)) * 100

    def _calculate_fcf(self, symbol: str) -> float:
        """
        計算自由現金流 (Free Cash Flow)
        
        FCF = 營業現金流 (TTM) - 資本支出 (TTM)
        
        Args:
            symbol: 股票代碼
            
        Returns:
            自由現金流（元）
        """
        df = self._get_fundamental_data(symbol)
        required = {'operating_cash_flow', 'capital_expenditure'}
        
        if df.empty or not required.issubset(df.columns) or len(df) < 4:
            self.logger.debug(f"Insufficient data for FCF calculation: {symbol}")
            return 0.0
        
        # 處理缺失值：用 0 填充
        df_clean = df[['operating_cash_flow', 'capital_expenditure']].fillna(0)
        
        ttm_ocf = df_clean['operating_cash_flow'].tail(4).sum()
        ttm_capex = df_clean['capital_expenditure'].tail(4).sum()
        
        fcf = ttm_ocf - ttm_capex
        self.logger.debug(f"{symbol} FCF: {fcf / 1e8:.2f}億")
        return fcf

    def _calculate_gross_margin_trend(self, symbol: str) -> float:
        """毛利率趨勢: 最近一季 vs 去年同季 (單位: %)"""
        df = self._get_fundamental_data(symbol)
        required = {'gross_profit', 'revenue'}
        if df.empty or not required.issubset(df.columns) or len(df) < 5:
            return 0.0
        
        df['margin'] = (df['gross_profit'] / df['revenue']) * 100
        latest_margin = df.iloc[-1]['margin']
        yoy_margin = df.iloc[-5]['margin']
        
        return latest_margin - yoy_margin

    def _calculate_debt_ratio(self, symbol: str) -> float:
        """負債比率 = 總負債 ÷ 總資產 × 100%"""
        df = self._get_fundamental_data(symbol)
        required = {'total_liabilities', 'total_assets'}
        if df.empty or not required.issubset(df.columns):
            return 100.0
            
        latest = df.iloc[-1]
        assets = latest['total_assets']
        return (latest['total_liabilities'] / assets * 100) if assets > 0 else 100.0

    def _calculate_revenue_yoy(self, symbol: str) -> float:
        """營收年增率 (最近一季 vs 去年同季)"""
        df = self._get_fundamental_data(symbol)
        if df.empty or 'revenue' not in df.columns or len(df) < 5:
            return 0.0
            
        latest_rev = df.iloc[-1]['revenue']
        yoy_rev = df.iloc[-5]['revenue']
        
        if yoy_rev <= 0: return 0.0
        return ((latest_rev - yoy_rev) / yoy_rev) * 100

    def _calculate_pe_relative(self, symbol: str) -> float:
        """
        PE 相對值 = 當前 PE 與歷史 PE 帶寬之比
        
        計算方法:
        1. 取得近 3-5 年歷史 PE 序列 (Price / TTM EPS)
        2. 計算 PE 序列之平均值 (mean) 與標準差 (std)
        3. 回傳當前 PE 相對值 (用於後續評分)
        """
        price_df = self.data_manager.read_symbol_partition(symbol)
        fund_df = self._get_fundamental_data(symbol)
        
        if price_df.empty or fund_df.empty or 'eps' not in fund_df.columns or len(fund_df) < 5:
            return 1.0
            
        # 1. 建立歷史 PE 序列
        # 價格數據是每日的，財報是每季的。我們將價格與財報按日期 merge
        price_df['date'] = pd.to_datetime(price_df['date'])
        fund_df['date'] = pd.to_datetime(fund_df['date'])
        
        # 為了計算 TTM EPS，我們對 fund_df 進行 rolling sum
        fund_df = fund_df.sort_values('date')
        fund_df['ttm_eps'] = fund_df['eps'].rolling(window=4).sum()
        
        # 合併數據以便計算每日 PE
        # 使用 merge_asof 確保每個價格對應到當時最新的 TTM EPS
        merged = pd.merge_asof(
            price_df.sort_values('date'),
            fund_df[['date', 'ttm_eps']].dropna(),
            on='date',
            direction='backward'
        )
        
        merged['pe'] = merged['close'] / merged['ttm_eps']
        # 過濾不合理的 PE (負值或極端值)
        pe_series = merged[merged['pe'] > 0]['pe'].tail(252 * 3) # 取近三年數據
        
        if pe_series.empty:
            return 1.0
            
        mean_pe = pe_series.mean()
        std_pe = pe_series.std()
        current_pe = merged['pe'].iloc[-1]
        
        if pd.isna(current_pe) or current_pe <= 0:
            return 2.0 # PE 無意義，給予較重處份
            
        # 回傳當前 PE 相對於平均值的偏離程度 (單位為 std)
        # 用於後續 _score_factor 判定
        # 比平均值低 1 個標差 -> (current - mean)/std = -1.0
        # 比平均值高 1 個標差 -> 1.0
        if std_pe > 0:
            relative_val = (current_pe - mean_pe) / std_pe
        else:
            relative_val = current_pe / mean_pe if mean_pe > 0 else 1.0
            
        return relative_val

    def _score_factor(self, factor_name: str, raw_value: float) -> int:
        """
        將因子原始值轉換為 1-5 分
        
        評分規則參考台股實際財務指標分佈情況調整
        
        Args:
            factor_name: 因子名稱
            raw_value: 因子原始值
            
        Returns:
            評分 (1-5 分)
        """
        # 完整評分規則：涵蓋所有 7 個因子
        scoring_rules = {
            # ROE (%) - 越高越好
            'roe': [(20, 5), (15, 4), (10, 3), (5, 2), (-float('inf'), 1)],
            
            # EPS YoY (%) - 越高越好
            'eps_yoy': [(30, 5), (15, 4), (0, 3), (-10, 2), (-float('inf'), 1)],
            
            # FCF (億) - 越高越好，以億為單位
            'fcf': [(5_000_000_000, 5), (1_000_000_000, 4), (0, 3), (-1_000_000_000, 2), (-float('inf'), 1)],
            
            # Gross Margin Trend (%) - 毛利率變化，越高越好
            'gross_margin_trend': [(2.0, 5), (0.5, 4), (-0.5, 3), (-2.0, 2), (-float('inf'), 1)],
            
            # Revenue YoY (%) - 越高越好
            'revenue_yoy': [(20, 5), (10, 4), (0, 3), (-5, 2), (-float('inf'), 1)],
            
            # Debt Ratio (%) - 越低越好（反向評分）
            'debt_ratio': [(30, 5), (50, 4), (70, 3), (85, 2), (float('inf'), 1)],
            
            # PE Relative (標準差偏離) - 越低越好，負值表示被低估
            'pe_relative': [(-1.0, 5), (0.0, 4), (1.0, 3), (2.0, 2), (float('inf'), 1)]
        }

        rules = scoring_rules.get(factor_name, [])
        
        if not rules:
            self.logger.warning(f"No scoring rules found for factor: {factor_name}")
            return 3  # 預設中等分數
        
        # 反向評分因子（越低越好）
        reverse_factors = ['debt_ratio', 'pe_relative']
        
        for threshold, score in rules:
            if factor_name in reverse_factors:
                # 越低越好：raw_value <= threshold 才能得分
                if raw_value <= threshold:
                    return score
            else:
                # 越高越好：raw_value >= threshold 才能得分
                if raw_value >= threshold:
                    return score
        
        return 1  # 最低分



if __name__ == '__main__':
    print("FactorEngine 模組已載入")
