"""
股票名稱映射工具

從 docs/500_stocks.txt 載入股票代號與中文名稱對照表，
提供快速查詢功能。
"""

from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class StockNameMapper:
    """股票名稱映射器"""
    
    def __init__(self, stock_list_path: Optional[Path] = None):
        """
        初始化股票名稱映射器
        
        Args:
            stock_list_path: 股票清單檔案路徑，預設為 docs/500_stocks.txt
        """
        if stock_list_path is None:
            # 預設路徑：從 src/utils 往上兩層到專案根目錄
            stock_list_path = Path(__file__).parent.parent.parent / 'docs' / '500_stocks.txt'
        
        self.stock_list_path = stock_list_path
        self._name_map: Optional[Dict[str, str]] = None
    
    def _load_stock_names(self) -> Dict[str, str]:
        """
        從檔案載入股票名稱對照表
        
        Returns:
            dict: {股票代號: 中文名稱}
        """
        name_map = {}
        
        if not self.stock_list_path.exists():
            logger.warning(f"股票清單檔案不存在: {self.stock_list_path}")
            return name_map
        
        try:
            with open(self.stock_list_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 格式: "股票代號 中文名稱"
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        symbol, name = parts
                        name_map[symbol] = name
            
            logger.info(f"成功載入 {len(name_map)} 檔股票名稱")
        except Exception as e:
            logger.error(f"載入股票名稱失敗: {e}")
        
        return name_map
    
    @property
    def name_map(self) -> Dict[str, str]:
        """取得股票名稱對照表（使用快取）"""
        if self._name_map is None:
            self._name_map = self._load_stock_names()
        return self._name_map
    
    def get_stock_name(self, symbol: str) -> str:
        """
        根據股票代號取得中文名稱
        
        Args:
            symbol: 股票代號（字串或整數）
            
        Returns:
            中文股票名稱，若找不到則返回代號本身
        """
        # 確保 symbol 為字串格式
        symbol_str = str(symbol)
        
        return self.name_map.get(symbol_str, symbol_str)
    
    def reload(self):
        """重新載入股票名稱對照表"""
        self._name_map = None
        logger.info("股票名稱對照表已重新載入")


# 全域單例實例
_global_mapper: Optional[StockNameMapper] = None


def get_stock_name(symbol: str) -> str:
    """
    獲取股票中文名稱（使用全域單例）
    
    Args:
        symbol: 股票代號
        
    Returns:
        中文股票名稱
    """
    global _global_mapper
    
    if _global_mapper is None:
        _global_mapper = StockNameMapper()
    
    return _global_mapper.get_stock_name(symbol)


def load_stock_names(stock_list_path: Optional[Path] = None) -> Dict[str, str]:
    """
    載入股票名稱對照表
    
    Args:
        stock_list_path: 股票清單檔案路徑
        
    Returns:
        dict: {股票代號: 中文名稱}
    """
    mapper = StockNameMapper(stock_list_path)
    return mapper.name_map


if __name__ == '__main__':
    # 測試功能
    logging.basicConfig(level=logging.INFO)
    
    print("測試股票名稱映射:")
    test_symbols = ['2330', '2317', '2454', '1102', '9999']
    
    for symbol in test_symbols:
        name = get_stock_name(symbol)
        print(f"  {symbol}: {name}")
