"""
策略掃描與選股腳本

執行時機：每日 16:00
功能：
    1. 載入配置與數據
    2. 執行三層篩選
    3. 生成買賣訊號
    4. 輸出選股結果
    5. 發送通知

參考：docs/Implementation.md 第 4.2 節
"""

import logging
import json
import os
from datetime import datetime, date
from pathlib import Path

from src.parquet_manager import ParquetManager
from src.factors import FactorEngine
from src.screener import StockScreener
from src.notification import NotificationService

def run_stock_screening():
    """
    執行選股策略
    """
    # 1. 設置路徑
    base_dir = Path(__file__).parent.parent
    report_dir = base_dir / 'reports' / 'selections'
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. 初始化組件
    data_manager = ParquetManager(base_path='data')
    factor_engine = FactorEngine(data_manager=data_manager)
    screener = StockScreener(factor_engine=factor_engine, data_manager=data_manager)
    
    # 載入 API 密鑰用於通知
    config_path = base_dir / 'config' / 'api_keys.json'
    notifier = None
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        notifier = NotificationService(config)

    logger = logging.getLogger(__name__)
    logger.info("開始執行選股流程...")

    try:
        # 3. 定義初始股票池 (Universe)
        history_path = base_dir / 'data' / 'history'
        if not history_path.exists():
            logger.error("找不到歷史數據目錄，請先執行 update_data.py")
            return
            
        universe = [d.name.split('=')[1] for d in history_path.iterdir() if d.is_dir() and 'symbol=' in d.name]
        
        if not universe:
            logger.warning("股票池為空，可能尚未下載數據。")
            return

        # 4. 執行篩選
        results_df = screener.screen_stocks(universe=universe)
        
        if results_df.empty:
            msg = f"📉 {date.today()} 選股結束：今日無符合條件的股票。"
            logger.info(msg)
            if notifier: notifier.send_telegram(msg)
            return

        # 5. 保存結果
        today_str = date.today().strftime("%Y-%m-%d")
        file_path = report_dir / f"selections_{today_str}.csv"
        results_df.to_csv(file_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"選股完成！共選出 {len(results_df)} 檔股票。結果儲存於: {file_path}")
        
        # 6. 構造通知訊息
        strong_buys = results_df[results_df['signal'] == 'STRONG_BUY']
        
        msg = f"🚀 <b>FinGear 選股日報 ({today_str})</b>\n\n"
        msg += f"共選出 {len(results_df)} 檔潛力股\n"
        
        if not strong_buys.empty:
            msg += "\n🔥 <b>今日熱門 (STRONG_BUY):</b>\n"
            for _, row in strong_buys.iterrows():
                msg += f"• <code>{row['symbol']}</code> Score: {row['fundamental_score']:.1f} | Bias: {row['bias_60']:.2f}%\n"
        else:
            msg += "\n📋 <b>今日精選 (前 3 名):</b>\n"
            for _, row in results_df.head(3).iterrows():
                msg += f"• <code>{row['symbol']}</code> {row['signal']} | Score: {row['fundamental_score']:.1f}\n"

        msg += f"\n完整清單已儲存於 CSV 報表。"
        
        if notifier:
            notifier.send_telegram(msg)
            logger.info("Telegram 通知已發送")

    except Exception as e:
        logger.error(f"策略掃描失敗: {e}", exc_info=True)
        if notifier: notifier.send_telegram(f"❌ 策略掃描失敗: {str(e)}")


def main():
    """主函數"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    run_stock_screening()

if __name__ == '__main__':
    main()


