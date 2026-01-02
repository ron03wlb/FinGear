# FinGear - 台股量化分析系統

> 基於無伺服器架構的台股數據庫與智慧選股系統

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)

## 系統概述

FinGear 是一套專為個人投資者設計的台股量化分析系統，透過無資料庫架構（No-DB）實現：

- 📊 **全市場數據追蹤**：自動維護市值前 500 大台股企業數據庫
- 🎯 **多因子智慧選股**：結合基本面、籌碼面、技術面三層篩選
- 🚀 **零維護成本**：無需架設資料庫伺服器，僅需本地 Python 環境
- ⚡ **高效能查詢**：採用 Apache Parquet 列式儲存，查詢速度提升 10 倍以上

## 快速開始

### 環境需求

- Python 3.8 或以上
- 硬碟空間至少 10GB
- 穩定的網路連線

### 安裝步驟

1. 克隆專案
```bash
git clone https://github.com/ron03wlb/FinGear.git
cd FinGear
```

2. 建立虛擬環境
```bash
python -m venv fingear_env
# Windows
fingear_env\Scripts\activate
# macOS/Linux
source fingear_env/bin/activate
```

3. 安裝依賴套件
```bash
pip install -r requirements.txt
```

4. 配置 API 金鑰
```bash
cp config/api_keys.example.json config/api_keys.json
# 編輯 api_keys.json，填入永豐金 Shioaji API 憑證
```

5. 執行初次數據下載
```bash
python scripts/update_data.py
```

## 專案結構

詳細架構請參閱 [Requirement/Overview.md](Requirement/Overview.md)

```
FinGear/
├── config/              # 配置檔案
├── data/                # 數據儲存區（Parquet 分區）
├── src/                 # 核心 Python 模組
├── scripts/             # 自動化執行腳本
├── tests/               # 單元測試與集成測試
└── reports/             # 選股結果與績效追蹤
```

## 核心功能

### 三層選股邏輯

1. **Layer 1: 基本面篩選**
   - 7 因子綜合評分（PE 估值 30%、ROE 15%、EPS YoY 15% 等）
   - 價值投資導向，強調低估值
   - Top 500 → Top 30

2. **Layer 2: 籌碼面驗證**
   - 多因子評分系統（投信連買、外資態度、自營商動向等）
   - 通過門檻：60 分以上

3. **Layer 3: 技術面位階**
   - 6 大技術指標綜合評分（均線、MACD、RSI、KD、量能、布林通道）
   - 訊號分級：強力買進、買進、觀察、持有、減碼

### 自動化排程

- **每日 15:00**：自動更新行情與籌碼數據
- **每日 16:00**：執行選股策略並推送通知

## 文檔

- [系統總覽與建置指南](Requirement/Overview.md)
- [實作架構文件](Requirement/Implementation.md)
- [財務指標定義](Requirement/FunctionalIndicators.md)

## 技術棧

| 層級 | 技術選型 |
|------|---------|
| 程式語言 | Python 3.8+ |
| 行情 API | Shioaji (永豐金) |
| 數據儲存 | Apache Parquet |
| 數據處理 | pandas, numpy |
| 技術指標 | pandas-ta / ta-lib |
| 排程管理 | schedule |
| 通知推送 | Line Notify, Telegram Bot |

## 授權條款

本專案採用 [Apache License 2.0](LICENSE) 授權。

## 貢獻指南

歡迎提交 Issue 和 Pull Request！

## 聯絡資訊

- GitHub: [ron03wlb/FinGear](https://github.com/ron03wlb/FinGear)
