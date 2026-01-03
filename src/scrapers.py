import requests
import pandas as pd
import logging
from datetime import datetime
from typing import Optional

class ChipDataScraper:
    """
    籌碼數據爬蟲 - 抓取三大法人與集保大戶持股
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def scrape_institutional_trades(self, date_str: str) -> pd.DataFrame:
        """
        抓取上市與上櫃股票三大法人買賣超
        """
        # 1. 抓取上市 (TWSE)
        twse_df = self._scrape_twse(date_str)
        # 2. 抓取上櫃 (TPEx)
        tpex_df = self._scrape_tpex(date_str)
        
        if twse_df.empty and tpex_df.empty:
            return pd.DataFrame()
            
        return pd.concat([twse_df, tpex_df]).reset_index(drop=True)

    def _scrape_twse(self, date_str: str) -> pd.DataFrame:
        query_date = date_str.replace('-', '')
        # 使用瀏覽器感知的最新 RWD URL
        url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={query_date}&selectType=ALL&response=json"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code != 200: return pd.DataFrame()
            data = response.json()
            
            if data['stat'] != 'OK': return pd.DataFrame()
            
            df = pd.DataFrame(data['data'], columns=data['fields'])
            # 欄位：證券代號, 證券名稱, 外陸資買進股數, 外陸資賣出股數, 外陸資買賣超股數, ...
            # 近年 TWSE 格式：代號(0), 外資超(4), 投信超(10), 自營超(11), 合計(15)
            # 注意：這裡需根據 fields 動態定位更好，暫用索引
            df = df.iloc[:, [0, 4, 10, 11, 15]]
            df.columns = ['symbol', 'foreign_net', 'trust_net', 'dealer_net', 'total_net']
            
            for col in ['foreign_net', 'trust_net', 'dealer_net', 'total_net']:
                df[col] = df[col].str.replace(',', '').astype(int)
            
            df['date'] = date_str
            df['symbol'] = df['symbol'].str.strip()
            return df
        except Exception as e:
            self.logger.error(f"TWSE 抓取異常: {e}", exc_info=True)
            return pd.DataFrame()

    def _scrape_tpex(self, date_str: str) -> pd.DataFrame:
        # 上櫃使用民國年格式 114/12/30
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        minguo_date = f"{dt.year - 1911}/{dt.strftime('%m/%d')}"
        url = f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&o=json&se=EW&t=D&d={minguo_date}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            data = response.json()
            if not data.get('aaData'): return pd.DataFrame()
            
            df = pd.DataFrame(data['aaData'])
            # 上櫃格式：代號(0), 外資(9), 投信(10), 自營(11), 合計(19)
            df = df.iloc[:, [0, 9, 10, 11, 19]]
            df.columns = ['symbol', 'foreign_net', 'trust_net', 'dealer_net', 'total_net']
            
            for col in ['foreign_net', 'trust_net', 'dealer_net', 'total_net']:
                df[col] = df[col].str.replace(',', '').astype(int)
            
            df['date'] = date_str
            df['symbol'] = df['symbol'].str.strip()
            return df
        except Exception as e:
            self.logger.error(f"TPEx 抓取異常: {e}", exc_info=True)
            return pd.DataFrame()

    def scrape_tdcc_shareholding(self) -> pd.DataFrame:
        """
        從 TDCC Open Data 抓取最新集保戶股權分散表
        """
        url = "https://opendata.tdcc.com.tw/getOD.ashx?id=1-5"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            from io import BytesIO
            # TDCC Open Data 現在多為 UTF-8 或帶 BOM
            df = pd.read_csv(BytesIO(response.content))
            
            # 自動偵測日期欄位
            if '資料日期' in df.columns:
                df = df.rename(columns={
                    '資料日期': 'date', 
                    '證券代號': 'symbol', 
                    '持股分級': 'level', 
                    '占集保庫存數比例%': 'ratio'
                })

            
            # 過濾 1000 張以上 (級別 15)
            major_df = df[df['level'] == 15].copy()
            
            # 日期處理 (TDCC 可能為 YYYYMMDD)
            major_df['date'] = major_df['date'].astype(str)
            major_df['date'] = pd.to_datetime(major_df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            major_df['symbol'] = major_df['symbol'].astype(str).str.strip()
            
            major_df = major_df[['date', 'symbol', 'ratio']]
            major_df.columns = ['date', 'symbol', 'major_ratio']
            return major_df
        except Exception as e:
            self.logger.error(f"TDCC 抓取異常: {e}", exc_info=True)
            return pd.DataFrame()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    scraper = ChipDataScraper()
    df = scraper.scrape_institutional_trades("2025-12-30")
    if not df.empty:
        print(df.head())
