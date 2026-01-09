#!/bin/bash
# FinGear 排程器快速啟動腳本

# 設置顏色輸出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}   FinGear 資料更新排程器 - 啟動腳本${NC}"
echo -e "${GREEN}===========================================${NC}\n"

# 檢查虛擬環境
if [ ! -d "venv" ]; then
    echo -e "${RED}錯誤: 找不到虛擬環境${NC}"
    echo "請先執行: python -m venv venv"
    exit 1
fi

# 啟動虛擬環境
source venv/bin/activate

# 檢查依賴
echo -e "${YELLOW}檢查依賴套件...${NC}"
if ! python -c "import apscheduler" 2>/dev/null; then
    echo -e "${YELLOW}安裝 APScheduler...${NC}"
    pip install APScheduler==3.10.4
fi

# 檢查配置檔案
if [ ! -f "config/api_keys.json" ]; then
    echo -e "${RED}錯誤: 找不到配置檔案 config/api_keys.json${NC}"
    echo "請先複製 config/api_keys.example.json 並填入 API 金鑰"
    exit 1
fi

# 建立 logs 目錄
mkdir -p logs

# 詢問啟動模式
echo -e "\n${YELLOW}請選擇啟動模式:${NC}"
echo "1) 前台運行（測試模式，按 Ctrl+C 停止）"
echo "2) 後台運行（生產模式，使用 nohup）"
read -p "請選擇 [1/2]: " mode

if [ "$mode" = "2" ]; then
    # 後台運行
    echo -e "\n${GREEN}以後台模式啟動排程器...${NC}"
    nohup python scripts/scheduler.py > logs/scheduler.log 2>&1 &
    PID=$!
    echo -e "${GREEN}排程器已啟動！PID: $PID${NC}"
    echo -e "${YELLOW}查看日誌: tail -f logs/scheduler.log${NC}"
    echo -e "${YELLOW}停止排程器: kill $PID${NC}"
else
    # 前台運行
    echo -e "\n${GREEN}以前台模式啟動排程器...${NC}"
    echo -e "${YELLOW}按 Ctrl+C 停止排程器${NC}\n"
    python scripts/scheduler.py
fi
