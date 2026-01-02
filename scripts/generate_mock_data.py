
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parquet_manager import ParquetManager

def generate_mock_data():
    """Generates complete mock data for Fundamentals, Chips, and Shareholding."""
    manager = ParquetManager(base_path='data')
    
    symbols = ["2330", "2317", "2454", "2308", "2303", "2881", "2882"]
    
    # 1. Fundamentals (Quarterly)
    fund_dates = pd.date_range(end='2025-09-30', periods=8, freq='QE')
    
    # 2. Chips (Daily)
    chip_dates = pd.date_range(end='2025-12-31', periods=20, freq='D')
    
    # 3. Shareholding (Weekly)
    share_dates = pd.date_range(end='2025-12-31', periods=8, freq='W-SUN')

    print(f"Generating data for {len(symbols)} symbols...")

    for symbol in symbols:
        # --- Fundamentals ---
        revenue = np.random.uniform(1000, 5000, 8)
        gross_profit = revenue * np.random.uniform(0.3, 0.6, 8)
        operating_expense = revenue * np.random.uniform(0.1, 0.2, 8)
        operating_income = gross_profit - operating_expense
        net_income = operating_income * 0.8
        
        total_assets = revenue * 4
        equity = total_assets * 0.6
        total_liabilities = total_assets - equity
        
        shares_outstanding = 100
        eps = net_income / shares_outstanding
        
        operating_cash_flow = net_income * 1.2
        capital_expenditure = operating_cash_flow * 0.5
        investing_cash_flow = -capital_expenditure
        financing_cash_flow = - (net_income * 0.3)
        cash_equivalents = np.random.uniform(500, 1000, 8)

        fund_data = {
            'date': fund_dates,
            'revenue': revenue,
            'gross_profit': gross_profit,
            'operating_income': operating_income,
            'net_income': net_income,
            'operating_expense': operating_expense,
            'eps': eps,
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'equity': equity,
            'operating_cash_flow': operating_cash_flow,
            'investing_cash_flow': investing_cash_flow,
            'financing_cash_flow': financing_cash_flow,
            'capital_expenditure': capital_expenditure,
            'cash_equivalents': cash_equivalents
        }
        
        # 2330 Special Logic (Fundamentals)
        if symbol == "2330":
            growth = np.linspace(1.0, 1.5, 8)
            fund_data['revenue'] = fund_data['revenue'] * growth
            fund_data['gross_profit'] = fund_data['revenue'] * 0.55
            fund_data['net_income'] = fund_data['revenue'] * 0.40
            fund_data['eps'] = fund_data['net_income'] / shares_outstanding
            fund_data['equity'] = fund_data['total_assets'] * 0.7
            fund_data['total_liabilities'] = fund_data['total_assets'] - fund_data['equity']

        manager.write_fundamental_data(symbol, pd.DataFrame(fund_data))

        # --- Chips ---
        chip_data = {
            'date': chip_dates,
            'foreign_net': np.random.uniform(-1000, 1000, 20),
            'trust_net': np.random.uniform(-200, 500, 20),
            'dealer_net': np.random.uniform(-500, 500, 20)
        }
        chip_df = pd.DataFrame(chip_data)
        chip_df['total_net'] = chip_df['foreign_net'] + chip_df['trust_net'] + chip_df['dealer_net']
        
        # 2330 Special Logic (Chips)
        if symbol == "2330":
             # Last 5 days strong buy
            chip_df.iloc[-5:, chip_df.columns.get_loc('total_net')] = 5000 
            
        manager.write_chip_data(symbol, chip_df)

        # --- Shareholding ---
        share_data = {
            'date': share_dates,
            'major_ratio': np.random.uniform(40, 70, len(share_dates))
        }
        share_df = pd.DataFrame(share_data)

        # 2330 Special Logic (Shareholding)
        if symbol == "2330":
            share_df['major_ratio'] = sorted(share_df['major_ratio']) # Increasing
            
        manager.write_shareholding_data(symbol, share_df)
        
        print(f"✅ Generated mock data for {symbol}")

if __name__ == '__main__':
    generate_mock_data()
