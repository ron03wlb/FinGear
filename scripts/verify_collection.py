"""
驗證基本面數據收集結果

功能：
    1. 檢查 500_stocks.txt 中股票的數據收集完整度
    2. 驗證數據結構和必要欄位
    3. 識別失敗或缺失的股票
    4. 生成摘要統計報告
"""

import sys
from pathlib import Path
from typing import List, Dict
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parquet_manager import ParquetManager


def load_stock_list(file_path: str) -> List[str]:
    """從 500_stocks.txt 載入股票清單"""
    symbols = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split()
                if parts and parts[0].isdigit() and len(parts[0]) == 4:
                    symbols.append(parts[0])
    return symbols


def check_data_availability(symbols: List[str], data_manager: ParquetManager) -> Dict:
    """檢查每檔股票的數據狀態"""
    results = {
        'collected': [],
        'missing': [],
        'details': []
    }
    
    for symbol in symbols:
        try:
            # 嘗試讀取數據
            df = data_manager.read_fundamental_data(symbol)
            
            if df is not None and not df.empty:
                # 檢查數據完整性
                record_count = len(df)
                columns = list(df.columns)
                date_range = f"{df['date'].min()} to {df['date'].max()}" if 'date' in df.columns else "N/A"
                
                results['collected'].append(symbol)
                results['details'].append({
                    'symbol': symbol,
                    'records': record_count,
                    'columns': len(columns),
                    'date_range': date_range,
                    'has_eps': 'eps' in columns,
                    'has_revenue': 'revenue' in columns,
                    'has_equity': 'equity' in columns
                })
            else:
                results['missing'].append(symbol)
                
        except FileNotFoundError:
            results['missing'].append(symbol)
        except Exception as e:
            print(f"Error checking {symbol}: {e}")
            results['missing'].append(symbol)
    
    return results


def print_summary_report(symbols: List[str], results: Dict):
    """輸出摘要報告"""
    total = len(symbols)
    collected = len(results['collected'])
    missing = len(results['missing'])
    coverage_rate = (collected / total * 100) if total > 0 else 0
    
    print("=" * 70)
    print("基本面數據收集驗證報告")
    print("=" * 70)
    print(f"\n📊 總體統計:")
    print(f"  - 股票總數: {total}")
    print(f"  - 已收集: {collected}")
    print(f"  - 缺失: {missing}")
    print(f"  - 覆蓋率: {coverage_rate:.1f}%")
    
    if results['details']:
        print(f"\n📈 數據品質:")
        df_details = pd.DataFrame(results['details'])
        
        print(f"  - 平均記錄數: {df_details['records'].mean():.1f}")
        print(f"  - 平均欄位數: {df_details['columns'].mean():.1f}")
        print(f"  - EPS 欄位覆蓋: {df_details['has_eps'].sum()}/{collected}")
        print(f"  - 營收欄位覆蓋: {df_details['has_revenue'].sum()}/{collected}")
        print(f"  - 股東權益欄位覆蓋: {df_details['has_equity'].sum()}/{collected}")

        # 新增：列出缺少營收的股票
        missing_revenue = [d['symbol'] for d in results['details'] if not d['has_revenue']]
        if missing_revenue:
            print(f"\n⚠️  缺失營收欄位之股票 ({len(missing_revenue)} 檔):")
            print(f"  - {', '.join(missing_revenue)}")
    
    if missing > 0:
        print(f"\n❌ 檔案缺失股票列表 ({missing} 檔):")
        for symbol in results['missing']:
            print(f"  - {symbol}")
    else:
        print(f"\n✅ 所有股票檔案皆已存在！")
    
    print("\n" + "=" * 70)
    
    # 抽樣顯示
    if results['details']:
        print("\n📋 數據抽樣 (前 5 檔):")
        sample_df = pd.DataFrame(results['details'][:5])
        print(sample_df.to_string(index=False))
    
    print("\n" + "=" * 70)


def verify_data_structure(data_manager: ParquetManager, symbols: List[str]):
    """驗證數據結構的一致性"""
    print("\n🔍 驗證數據結構...")
    
    # 抽樣檢查幾檔股票
    sample_symbols = symbols[:5] if len(symbols) > 5 else symbols
    
    for symbol in sample_symbols:
        try:
            df = data_manager.read_fundamental_data(symbol)
            if df is not None and not df.empty:
                print(f"\n  {symbol}:")
                print(f"    - 記錄數: {len(df)}")
                print(f"    - 欄位: {', '.join(df.columns.tolist()[:8])}...")
                print(f"    - 日期範圍: {df['date'].min()} ~ {df['date'].max()}")
                
                # 檢查資料型態
                if 'eps' in df.columns:
                    print(f"    - 最新 EPS: {df['eps'].iloc[-1]:.2f}")
        except Exception as e:
            print(f"  {symbol}: Error - {e}")


def main():
    """主函數"""
    # 載入股票清單
    stock_file = Path(__file__).parent.parent / 'docs' / '500_stocks.txt'
    
    if not stock_file.exists():
        print(f"❌ 錯誤: 找不到檔案 {stock_file}")
        sys.exit(1)
    
    print("📂 載入股票清單...")
    symbols = load_stock_list(stock_file)
    print(f"✓ 載入 {len(symbols)} 檔股票")
    
    # 初始化數據管理器
    data_manager = ParquetManager(base_path='data')
    
    # 檢查數據可用性
    print("\n🔎 檢查數據收集狀況...")
    results = check_data_availability(symbols, data_manager)
    
    # 輸出摘要報告
    print_summary_report(symbols, results)
    
    # 驗證數據結構
    if results['collected']:
        verify_data_structure(data_manager, results['collected'])
    
    # 返回狀態碼
    if results['missing']:
        sys.exit(1)  # 有缺失數據
    else:
        sys.exit(0)  # 全部成功


if __name__ == '__main__':
    main()
