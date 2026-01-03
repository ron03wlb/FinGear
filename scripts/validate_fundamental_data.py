"""
基本面數據驗證腳本

功能：
    1. 掃描 data/fundamentals/ 目錄，統計數據覆蓋率
    2. 檢查每支股票的數據完整性（必要欄位、時間範圍）
    3. 識別異常值（如負數營收、異常 PE）
    4. 產生數據質量報告

參考：Implementation Plan - Data Quality Monitoring
"""

import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import pandas as pd
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parquet_manager import ParquetManager


class FundamentalDataValidator:
    """基本面數據驗證器"""
    
    REQUIRED_COLUMNS = {
        'date', 'eps', 'equity', 'total_assets'
    }
    
    RECOMMENDED_COLUMNS = {
        'revenue', 'gross_profit', 'operating_income', 'net_income',
        'total_liabilities', 'operating_cash_flow', 'capital_expenditure'
    }
    
    MIN_QUARTERS = 5  # 至少需要 5 個季度的數據（供 YoY 計算）
    
    def __init__(self, data_manager: ParquetManager):
        """
        初始化驗證器
        
        Args:
            data_manager: Parquet 數據管理器
        """
        self.data_manager = data_manager
        self.logger = logging.getLogger(__name__)
        self.validation_results = []
        
    def scan_all_stocks(self) -> List[str]:
        """
        掃描 fundamentals 目錄，獲取所有已下載的股票列表
        
        Returns:
            股票代碼列表
        """
        fundamentals_path = self.data_manager.fundamentals_path
        
        if not fundamentals_path.exists():
            self.logger.warning(f"Fundamentals directory not found: {fundamentals_path}")
            return []
        
        stocks = []
        for symbol_dir in fundamentals_path.iterdir():
            if symbol_dir.is_dir() and symbol_dir.name.startswith('symbol='):
                symbol = symbol_dir.name.split('=')[1]
                data_file = symbol_dir / 'data.parquet'
                if data_file.exists() and data_file.stat().st_size > 0:
                    stocks.append(symbol)
        
        return sorted(stocks)
    
    def validate_stock(self, symbol: str) -> Dict:
        """
        驗證單支股票的數據質量
        
        Args:
            symbol: 股票代碼
            
        Returns:
            驗證結果字典
        """
        result = {
            'symbol': symbol,
            'valid': False,
            'quarters': 0,
            'missing_required': [],
            'missing_recommended': [],
            'anomalies': [],
            'date_range': None
        }
        
        try:
            df = self.data_manager.read_fundamental_data(symbol)
            
            if df.empty:
                result['anomalies'].append('Empty DataFrame')
                return result
            
            # 檢查數據量
            result['quarters'] = len(df)
            
            # 檢查必要欄位
            existing_cols = set(df.columns)
            result['missing_required'] = list(self.REQUIRED_COLUMNS - existing_cols)
            result['missing_recommended'] = list(self.RECOMMENDED_COLUMNS - existing_cols)
            
            # 檢查日期範圍
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                result['date_range'] = (
                    df['date'].min().strftime('%Y-%m-%d'),
                    df['date'].max().strftime('%Y-%m-%d')
                )
            
            # 檢查數據異常
            self._check_anomalies(df, result)
            
            #判斷是否有效
            result['valid'] = (
                result['quarters'] >= self.MIN_QUARTERS and
                len(result['missing_required']) == 0 and
                len([a for a in result['anomalies'] if 'critical' in a.lower()]) == 0
            )
            
        except Exception as e:
            result['anomalies'].append(f'Validation error: {str(e)}')
            self.logger.error(f"Error validating {symbol}: {e}", exc_info=True)
        
        return result
    
    def _check_anomalies(self, df: pd.DataFrame, result: Dict):
        """
        檢測數據異常
        
        Args:
            df: 財務數據 DataFrame
            result: 驗證結果字典（會被修改）
        """
        # 檢查營收負值
        if 'revenue' in df.columns:
            negative_revenue = (df['revenue'] < 0).sum()
            if negative_revenue > 0:
                result['anomalies'].append(f'CRITICAL: {negative_revenue} quarters with negative revenue')
        
        # 檢查股東權益為 0 或負值
        if'equity' in df.columns:
            invalid_equity = (df['equity'] <= 0).sum()
            if invalid_equity > 0:
                result['anomalies'].append(f'CRITICAL: {invalid_equity} quarters with zero/negative equity')
        
        # 檢查總資產為 0 或負值
        if 'total_assets' in df.columns:
            invalid_assets = (df['total_assets'] <= 0).sum()
            if invalid_assets > 0:
                result['anomalies'].append(f'CRITICAL: {invalid_assets} quarters with zero/negative assets')
        
        # 檢查 EPS 極端值（> 100 或 < -50）
        if 'eps' in df.columns:
            extreme_eps = ((df['eps'] > 100) | (df['eps'] < -50)).sum()
            if extreme_eps > 0:
                result['anomalies'].append(f'WARNING: {extreme_eps} quarters with extreme EPS values')
        
        # 檢查缺失值
        null_counts = df.isnull().sum()
        for col, count in null_counts.items():
            if count > 0:
                pct = (count / len(df)) * 100
                if col in self.REQUIRED_COLUMNS:
                    result['anomalies'].append(f'CRITICAL: {col} has {count} NaN values ({pct:.1f}%)')
                elif pct > 50:  # 超過 50% 缺失
                    result['anomalies'].append(f'WARNING: {col} has {count} NaN values ({pct:.1f}%)')
    
    def validate_all(self) -> Dict:
        """
        驗證所有股票並產生彙總報告
        
        Returns:
            驗證彙總結果
        """
        stocks = self.scan_all_stocks()
        self.logger.info(f"Found {len(stocks)} stocks to validate")
        
        self.validation_results = []
        for symbol in stocks:
            result = self.validate_stock(symbol)
            self.validation_results.append(result)
        
        # 彙總統計
        summary = {
            'total_stocks': len(stocks),
            'valid_stocks': sum(1 for r in self.validation_results if r['valid']),
            'invalid_stocks': sum(1 for r in self.validation_results if not r['valid']),
            'average_quarters': sum(r['quarters'] for r in self.validation_results) / len(stocks) if stocks else 0,
            'critical_issues': sum(1 for r in self.validation_results 
                                   if any('CRITICAL' in a for a in r['anomalies']))
        }
        
        return summary
    
    def generate_report(self, output_path: str = 'reports/data_quality_report.md'):
        """
        產生 Markdown 格式的數據質量報告
        
        Args:
            output_path: 報告輸出路徑
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        summary = {
            'total_stocks': len(self.validation_results),
            'valid_stocks': sum(1 for r in self.validation_results if r['valid']),
            'invalid_stocks': sum(1 for r in self.validation_results if not r['valid']),
            'average_quarters': (sum(r['quarters'] for r in self.validation_results) / 
                                len(self.validation_results)) if self.validation_results else 0,
            'critical_issues': sum(1 for r in self.validation_results 
                                   if any('CRITICAL' in a for a in r['anomalies']))
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('# 基本面數據質量報告\n\n')
            f.write(f'**生成時間**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            
            # 彙總統計
            f.write('## 彙總統計\n\n')
            f.write(f'- 總股票數: {summary["total_stocks"]}\n')
            f.write(f'- 有效股票: {summary["valid_stocks"]} ✅\n')
            f.write(f'- 無效股票: {summary["invalid_stocks"]} ❌\n')
            f.write(f'- 平均季度數: {summary["average_quarters"]:.1f}\n')
            f.write(f'- 嚴重問題數: {summary["critical_issues"]}\n\n')
            
            success_rate = (summary['valid_stocks'] / summary['total_stocks'] * 100) if summary['total_stocks'] > 0 else 0
            f.write(f'**成功率**: {success_rate:.1f}%\n\n')
            
            # 有效股票列表
            valid_stocks = [r for r in self.validation_results if r['valid']]
            if valid_stocks:
                f.write('\n## 有效股票列表\n\n')
                f.write('| 股票代碼 | 季度數 | 日期範圍 |\n')
                f.write('|---------|-------|----------|\n')
                for r in valid_stocks:
                    date_range = f"{r['date_range'][0]} ~ {r['date_range'][1]}" if r['date_range'] else 'N/A'
                    f.write(f'| {r["symbol"]} | {r["quarters"]} | {date_range} |\n')
            
            # 無效或有問題的股票
            invalid_stocks = [r for r in self.validation_results if not r['valid']]
            if invalid_stocks:
                f.write('\n## 無效或有問題的股票\n\n')
                for r in invalid_stocks:
                    f.write(f'\n### {r["symbol"]}\n\n')
                    f.write(f'- 季度數: {r["quarters"]}\n')
                    
                    if r['missing_required']:
                        f.write(f'- 缺少必要欄位: {", ".join(r["missing_required"])}\n')
                    
                    if r['anomalies']:
                        f.write('- 異常:\n')
                        for anomaly in r['anomalies']:
                            f.write(f'  - {anomaly}\n')
        
        self.logger.info(f"Report generated: {output_file}")
        print(f'\n✓ 報告已生成: {output_file}')


def main():
    """主函數"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # 初始化
        data_manager = ParquetManager(base_path='data')
        validator = FundamentalDataValidator(data_manager)
        
        # 執行驗證
        logger.info("Starting data validation...")
        summary = validator.validate_all()
        
        # 輸出彙總
        print('\n' + '=' * 60)
        print('數據質量驗證彙總')
        print('=' * 60)
        print(f'總股票數: {summary["total_stocks"]}')
        print(f'有效股票: {summary["valid_stocks"]} ✅')
        print(f'無效股票: {summary["invalid_stocks"]} ❌')
        print(f'平均季度數: {summary["average_quarters"]:.1f}')
        print(f'嚴重問題數: {summary["critical_issues"]}')
        
        success_rate = (summary['valid_stocks'] / summary['total_stocks'] * 100) if summary['total_stocks'] > 0 else 0
        print(f'\n成功率: {success_rate:.1f}%')
        print('=' * 60)
        
        # 產生詳細報告
        validator.generate_report()
        
        # 返回狀態碼
        if summary['critical_issues'] > 0:
            logger.warning(f"Found {summary['critical_issues']} stocks with critical issues")
            sys.exit(1)
        else:
            logger.info("All validations passed!")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
