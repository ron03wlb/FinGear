"""
從 500_stocks.txt 提取股票代碼

功能：
    1. 讀取 docs/500_stocks.txt 檔案
    2. 提取股票代碼（第一欄）
    3. 驗證格式（4位數字）
    4. 輸出清單供後續使用
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def extract_stock_symbols(file_path: str) -> List[str]:
    """
    從檔案提取股票代碼
    
    Args:
        file_path: 股票清單檔案路徑
        
    Returns:
        股票代碼列表
    """
    symbols = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # 跳過空行
            if not line:
                continue
            
            # 提取第一個欄位（股票代碼）
            parts = line.split()
            if not parts:
                continue
            
            symbol = parts[0]
            
            # 驗證格式 (4位數字)
            if not symbol.isdigit() or len(symbol) != 4:
                print(f"Warning: Invalid symbol format at line {line_num}: {symbol}")
                continue
            
            symbols.append(symbol)
    
    return symbols


def main():
    """主函數"""
    # 檔案路徑
    stock_file = Path(__file__).parent.parent / 'docs' / '500_stocks.txt'
    
    if not stock_file.exists():
        print(f"Error: File not found: {stock_file}")
        sys.exit(1)
    
    # 提取股票代碼
    symbols = extract_stock_symbols(stock_file)
    
    # 顯示結果
    print(f"✓ Extracted {len(symbols)} stock symbols from {stock_file.name}")
    print(f"\nFirst 10 symbols: {', '.join(symbols[:10])}")
    print(f"Last 10 symbols: {', '.join(symbols[-10:])}")
    
    # 輸出完整清單（供後續使用）
    print("\n" + "="*60)
    print("Complete symbol list (space-separated):")
    print("="*60)
    print(' '.join(symbols))
    
    return symbols


if __name__ == '__main__':
    main()
