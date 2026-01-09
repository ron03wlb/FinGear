"""
選股篩選器模組

提供三層篩選邏輯，實現：
- Layer 1: 基本面篩選（7 因子綜合評分）
- Layer 2: 籌碼面驗證（法人 + 大戶）
- Layer 3: 技術面位階（乖離率 + KD/RSI）

參考：docs/Implementation.md 第 3.3 節
"""

import logging
from typing import List
import pandas as pd
from src.utils.stock_names import get_stock_name


class StockScreener:
    """
    選股篩選器

    職責：三層篩選邏輯、綜合評分、訊號生成
    設計模式：Pipeline Pattern

    Attributes:
        factor_engine: 因子計算引擎
        data_manager: 數據管理器

    Examples:
        >>> screener = StockScreener(factor_engine, data_manager)
        >>> results = screener.screen_stocks(universe=['2330', '2454', ...])
    """

    def __init__(self, factor_engine, data_manager):
        """
        初始化選股篩選器

        Args:
            factor_engine: 因子計算引擎
            data_manager: 數據管理器
        """
        self.factor_engine = factor_engine
        self.data_manager = data_manager
        self.logger = logging.getLogger(__name__)

    def screen_stocks(self, universe: List[str]) -> pd.DataFrame:
        """
        執行完整選股流程 (L1 -> L2 -> L3)
        """
        self.logger.info(f"開始選股流程，初始股票池: {len(universe)} 檔")

        # Layer 1: 基本面
        l1_candidates = self._layer1_fundamental_screen(universe)
        if l1_candidates.empty:
            self.logger.warning("Layer 1 篩選後無候選股")
            return pd.DataFrame()

        # Layer 2: 籌碼面
        l2_candidates = self._layer2_chip_filter(l1_candidates)
        if l2_candidates.empty:
            self.logger.warning("Layer 2 篩選後無候選股")
            return pd.DataFrame()

        # Layer 3: 技術面與訊號生成
        final_results = self._layer3_technical_position(l2_candidates)
        
        self.logger.info(f"選股流程結束，最終選出 {len(final_results)} 檔")
        return final_results

    def _layer1_fundamental_screen(self, universe: List[str]) -> pd.DataFrame:
        """
        Layer 1: 基本面與位階篩選
        1. 計算 7 因子綜合得分
        2. 過濾「昂貴」位階（pe_score < 4，即 PE > 歷史均值）
        3. 取得分前 30 名
        """
        results = []
        for symbol in universe:
            try:
                # 獲取詳細因子評分
                details = self.factor_engine.calculate_fundamental_details(symbol)
                score = details['total_score']
                factors = details['factors']

                # 檢查 PE 位階 (Stock Level)
                pe_score = factors.get('pe_relative', {}).get('score', 1)

                # 位階過濾：只保留「便宜 (5分)」或「合理 (4分)」
                if pe_score < 4:
                    self.logger.debug(f"{symbol} 位階過於昂貴 (PE Score: {pe_score}), 予以過濾")
                    continue

                results.append({
                    'symbol': symbol,
                    'stock_name': get_stock_name(symbol),
                    'fundamental_score': score,
                    'pe_score': pe_score,
                    'fundamental_details': factors  # 儲存詳細因子分數
                })
            except Exception as e:
                self.logger.error(f"Error scoring {symbol}: {e}", exc_info=True)

        df = pd.DataFrame(results)
        if df.empty: return df

        # 排序並取前 30
        return df.sort_values('fundamental_score', ascending=False).head(30)

    def _layer2_chip_filter(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """
        Layer 2: 籌碼面過濾（細化多因子評分）
        評分項目：
            1. 投信連續買超天數（權重 30%）
            2. 外資持倉態度（權重 25%）
            3. 自營商動向（權重 15%）
            4. 三大法人合計強度（權重 20%）
            5. 大戶持股趨勢（權重 10%）
        總分 >= 60 分通過
        """
        passed = []
        for _, row in candidates.iterrows():
            symbol = row['symbol']
            
            chip_score = 0
            chip_details = {}
            
            # 1. 籌碼數據載入
            chip_df = self.data_manager.read_chip_data(symbol)
            if chip_df.empty or len(chip_df) < 5:
                self.logger.warning(f"{symbol} 籌碼數據不足，設為 0 分")
                chip_score = 0
                recent_5d = pd.DataFrame()
            else:
                recent_5d = chip_df.tail(5)
            
            # === 因子 1: 投信連續買超天數 (0-30 分) ===
            trust_consecutive = 0
            if not recent_5d.empty:
                for i in range(len(recent_5d) - 1, -1, -1):
                    if recent_5d.iloc[i]['trust_net'] > 0:
                        trust_consecutive += 1
                    else:
                        break
            
            if trust_consecutive >= 5:
                chip_score += 30
                chip_details['trust_days'] = f"{trust_consecutive}連買(滿分)"
            elif trust_consecutive >= 3:
                chip_score += 20
                chip_details['trust_days'] = f"{trust_consecutive}連買"
            elif trust_consecutive >= 1:
                chip_score += 10
                chip_details['trust_days'] = f"{trust_consecutive}連買"
            else:
                chip_details['trust_days'] = "未買超"
            
            # === 因子 2: 外資持倉態度 (0-25 分) ===
            if not recent_5d.empty:
                foreign_5d_avg = recent_5d['foreign_net'].mean()
                foreign_latest = recent_5d.iloc[-1]['foreign_net']
                
                if foreign_5d_avg > 1000 and foreign_latest > 0:
                    chip_score += 25  # 持續買超且最近仍買
                    chip_details['foreign_status'] = "積極買超"
                elif foreign_5d_avg > 0:
                    chip_score += 15  # 平均買超
                    chip_details['foreign_status'] = "溫和買超"
                elif foreign_5d_avg > -1000:
                    chip_score += 5   # 小幅賣壓（可容忍）
                    chip_details['foreign_status'] = "小賣"
                else:
                    chip_details['foreign_status'] = "大賣"
            else:
                chip_details['foreign_status'] = "無數據"
            
            # === 因子 3: 自營商動向 (0-15 分) ===
            if not recent_5d.empty:
                dealer_5d_total = recent_5d['dealer_net'].sum()
                if dealer_5d_total > 0:
                    chip_score += 15
                    chip_details['dealer_status'] = "買超"
                elif dealer_5d_total > -500:
                    chip_score += 8
                    chip_details['dealer_status'] = "中立"
                else:
                    chip_details['dealer_status'] = "賣超"
            else:
                chip_details['dealer_status'] = "無數據"
            
            # === 因子 4: 三大法人合計強度 (0-20 分) ===
            if not recent_5d.empty:
                total_5d_sum = recent_5d['total_net'].sum()
                if total_5d_sum > 5000:
                    chip_score += 20
                    chip_details['total_strength'] = "強勁"
                elif total_5d_sum > 1000:
                    chip_score += 15
                    chip_details['total_strength'] = "穩健"
                elif total_5d_sum > 0:
                    chip_score += 10
                    chip_details['total_strength'] = "微弱"
                else:
                    chip_details['total_strength'] = "負值"
            else:
                chip_details['total_strength'] = "無數據"
            
            # === 因子 5: 大戶持股趨勢 (0-10 分) ===
            share_df = self.data_manager.read_shareholding_data(symbol)
            if not share_df.empty and len(share_df) >= 2:
                latest_ratio = share_df.iloc[-1]['major_ratio']
                prev_ratio = share_df.iloc[-2]['major_ratio']
                ratio_change = latest_ratio - prev_ratio
                
                if ratio_change > 0.5:
                    chip_score += 10
                    chip_details['share_trend'] = f"+{ratio_change:.2f}%"
                elif ratio_change >= 0:
                    chip_score += 5
                    chip_details['share_trend'] = f"+{ratio_change:.2f}%"
                else:
                    chip_details['share_trend'] = f"{ratio_change:.2f}%"
            else:
                chip_details['share_trend'] = "無數據"
            
            # === 不再過濾，所有股票都保留（籌碼面僅供參考）===
            row['chip_score'] = chip_score
            row['chip_details'] = str(chip_details)
            # 確保 fundamental_details 也被轉換為字符串
            if 'fundamental_details' in row:
                row['fundamental_details'] = str(row['fundamental_details'])
            passed.append(row)

            # 記錄籌碼面評分（僅供參考）
            self.logger.info(f"{symbol} 籌碼面評分 {chip_score}/100 - {chip_details}")

        return pd.DataFrame(passed)

    def _layer3_technical_position(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """
        Layer 3: 技術面指標多維度評估（不過濾，僅提供技術建議）
        評分項目：
            1. 均線趨勢（多頭排列）（25%）
            2. MACD 動能確認（20%）
            3. RSI 超買超賣偵測（15%）
            4. KD 指標狀態（15%）
            5. 量能放大驗證（15%）
            6. 布林通道位置（10%）

        技術建議（僅供參考）：
        總分 >= 65 分 → STRONG_BUY（強力買進）
        總分 50-64 分 → BUY（買進）
        總分 35-49 分 → WATCH（觀察）
        總分 < 35 分 → HOLD/REDUCE（持有/減碼）

        注意：所有通過籌碼面的股票都會保留，不會被技術面過濾
        """
        results = []
        import pandas_ta as ta

        for _, row in candidates.iterrows():
            symbol = row['symbol']
            try:
                df = self.data_manager.read_symbol_partition(symbol)
                if df.empty or len(df) < 120:
                    row['signal'] = 'DATA_INSUFFICIENT'
                    row['tech_score'] = 0
                    results.append(row)
                    continue

                tech_score = 0
                tech_details = {}
                
                # === 因子 1: 均線趨勢（25 分）===
                ma20 = df['close'].rolling(window=20).mean().iloc[-1]
                ma60 = df['close'].rolling(window=60).mean().iloc[-1]
                ma120 = df['close'].rolling(window=120).mean().iloc[-1]
                current_price = df['close'].iloc[-1]
                
                # 多頭排列檢查
                if current_price > ma20 > ma60 > ma120:
                    tech_score += 25
                    tech_details['ma_trend'] = "完美多頭"
                elif current_price > ma20 > ma60:
                    tech_score += 20
                    tech_details['ma_trend'] = "強勢多頭"
                elif current_price > ma60:
                    tech_score += 15
                    tech_details['ma_trend'] = "站上季線"
                elif current_price > ma120:
                    tech_score += 10
                    tech_details['ma_trend'] = "站上半年線"
                else:
                    tech_details['ma_trend'] = "空頭排列"
                
                # Bias 計算
                bias_60 = ((current_price - ma60) / ma60) * 100
                row['bias_60'] = bias_60
                tech_details['bias_60'] = f"{bias_60:.2f}%"
                
                # === 因子 2: MACD 動能（20 分）===
                macd = ta.macd(df['close'])
                if macd is not None and not macd.empty:
                    macd_line = macd['MACD_12_26_9'].iloc[-1]
                    signal_line = macd['MACDs_12_26_9'].iloc[-1]
                    histogram = macd['MACDh_12_26_9'].iloc[-1]
                    
                    if macd_line > signal_line and histogram > 0:
                        if histogram > macd['MACDh_12_26_9'].iloc[-2]:
                            tech_score += 20  # 金叉且柱狀放大
                            tech_details['macd'] = "強勁金叉"
                        else:
                            tech_score += 15  # 金叉但收斂
                            tech_details['macd'] = "金叉"
                    elif macd_line > 0:
                        tech_score += 10  # MACD 在零軸上
                        tech_details['macd'] = "多頭區"
                    else:
                        tech_details['macd'] = "空頭區"
                else:
                    tech_details['macd'] = "無數據"
                
                # === 因子 3: RSI 超買超賣（15 分）===
                rsi = ta.rsi(df['close'], length=14)
                if rsi is not None and not rsi.empty:
                    rsi_value = rsi.iloc[-1]
                    
                    if 40 <= rsi_value <= 70:
                        tech_score += 15  # 健康區間
                        tech_details['rsi'] = f"{rsi_value:.1f}(健康)"
                    elif 30 <= rsi_value < 40:
                        tech_score += 10  # 接近超賣，反彈機會
                        tech_details['rsi'] = f"{rsi_value:.1f}(接近超賣)"
                    elif rsi_value > 70:
                        tech_score += 5   # 超買警示
                        tech_details['rsi'] = f"{rsi_value:.1f}(超買)"
                    else:
                        tech_details['rsi'] = f"{rsi_value:.1f}(超賣)"
                else:
                    tech_details['rsi'] = "無數據"
                
                # === 因子 4: KD 指標（15 分）===
                kd = ta.stoch(df['high'], df['low'], df['close'])
                if kd is not None and not kd.empty:
                    k = kd['STOCHk_14_3_3'].iloc[-1]
                    d = kd['STOCHd_14_3_3'].iloc[-1]
                    row['k'], row['d'] = k, d
                    
                    if k > d and k < 80:
                        tech_score += 15  # 金叉且未超買
                        tech_details['kd'] = f"金叉({k:.1f})"
                    elif k > d:
                        tech_score += 10  # 金叉但超買
                        tech_details['kd'] = f"金叉超買({k:.1f})"
                    elif 20 <= k <= 50:
                        tech_score += 8   # 低檔整理
                        tech_details['kd'] = f"低檔({k:.1f})"
                    else:
                        tech_details['kd'] = f"死叉({k:.1f})"
                else:
                    row['k'], row['d'] = 0, 0
                    tech_details['kd'] = "無數據"
                
                # === 因子 5: 量能放大（15 分）===
                recent_5d_vol = df['volume'].tail(5).mean()
                prev_20d_vol = df['volume'].iloc[-25:-5].mean()
                
                if recent_5d_vol > prev_20d_vol * 1.5:
                    tech_score += 15  # 爆量
                    tech_details['volume'] = "爆量"
                elif recent_5d_vol > prev_20d_vol * 1.2:
                    tech_score += 12  # 量增
                    tech_details['volume'] = "量增"
                elif recent_5d_vol > prev_20d_vol:
                    tech_score += 8   # 溫和放大
                    tech_details['volume'] = "溫和放大"
                else:
                    tech_details['volume'] = "量縮"
                
                # === 因子 6: 布林通道（10 分）===
                bbands = ta.bbands(df['close'], length=20)
                if bbands is not None and not bbands.empty:
                    # pandas-ta 格式: BBU_20_2.0_2.0，確保取標量
                    bb_cols = bbands.columns
                    upper = bbands[bb_cols[bb_cols.str.startswith('BBU')][0]].iloc[-1]
                    middle = bbands[bb_cols[bb_cols.str.startswith('BBM')][0]].iloc[-1]
                    lower = bbands[bb_cols[bb_cols.str.startswith('BBL')][0]].iloc[-1]
                    
                    if lower < current_price < middle:
                        tech_score += 10  # 下軌至中軌，反彈空間大
                        tech_details['bbands'] = "下半部"
                    elif middle < current_price < (middle + upper) / 2:
                        tech_score += 8   # 中軌至 3/4 處
                        tech_details['bbands'] = "中上"
                    elif current_price < lower:
                        tech_score += 5   # 跌破下軌（超賣反彈）
                        tech_details['bbands'] = "破下軌"
                    else:
                        tech_details['bbands'] = "上軌附近"
                else:
                    tech_details['bbands'] = "無數據"
                
                # === 綜合訊號判定 ===
                row['tech_score'] = tech_score
                row['tech_details'] = str(tech_details)
                
                if tech_score >= 65:
                    row['signal'] = 'STRONG_BUY'
                elif tech_score >= 50:
                    row['signal'] = 'BUY'
                elif tech_score >= 35:
                    row['signal'] = 'WATCH'
                else:
                    if bias_60 > 20:
                        row['signal'] = 'OVERBOUGHT_REDUCE'
                    else:
                        row['signal'] = 'HOLD'

                # 記錄技術面評分（僅供參考，不影響是否入選）
                self.logger.info(f"{symbol} 技術建議 {tech_score}/100 → {row['signal']} - {tech_details}")
                results.append(row)
                
            except Exception as e:
                self.logger.error(f"Error in L3 for {symbol}: {e}", exc_info=True)
            
        return pd.DataFrame(results)

    def _calculate_bias(self, symbol: str, ma_period: int = 60) -> float:
        df = self.data_manager.read_symbol_partition(symbol)
        if df.empty or len(df) < ma_period: return 0.0
        ma = df['close'].rolling(window=ma_period).mean().iloc[-1]
        return ((df['close'].iloc[-1] - ma) / ma) * 100



if __name__ == '__main__':
    print("StockScreener 模組已載入")
