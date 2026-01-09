# FinGear 資料更新排程系統使用指南

## 概述

`scripts/scheduler.py` 提供完整的自動化資料更新排程系統，使用 APScheduler 實現靈活的任務排程。

## 排程任務列表

| 任務           | 執行時間     | 說明                                   |
| -------------- | ------------ | -------------------------------------- |
| 價格數據更新   | 每小時整點   | 僅在交易時間（週一~五 9:00-13:30）執行 |
| 基本面數據更新 | 每日 16:00   | 更新已追蹤股票的財務數據               |
| 籌碼數據更新   | 每日 15:30   | 更新三大法人買賣超數據                 |
| 大戶持股更新   | 每週五 18:00 | 更新集保大戶持股資料                   |
| 清理舊數據     | 每週日 02:00 | 清理 30 天前的時間分區數據             |
| 統計報告       | 每日 23:00   | 輸出當日更新統計                       |

## 使用方法

### 1. 安裝依賴

```bash
pip install APScheduler==3.10.4
```

### 2. 啟動排程器

```bash
# 前台運行（用於測試）
python scripts/scheduler.py

# 後台運行（生產環境）
nohup python scripts/scheduler.py > logs/scheduler.log 2>&1 &

# 或使用 systemd/supervisor 管理
```

### 3. 停止排程器

按 `Ctrl+C` 或發送 SIGTERM 信號：

```bash
# 找到進程 ID
ps aux | grep scheduler.py

# 停止進程
kill <PID>
```

## 配置說明

### 修改排程時間

編輯 `scripts/scheduler.py` 中的 `setup_schedules()` 方法：

```python
# 修改基本面數據更新時間為每日 17:00
self.scheduler.add_job(
    self.update_fundamental_data,
    trigger=CronTrigger(hour=17, minute=0, timezone='Asia/Taipei'),
    ...
)
```

### 調整更新範圍

修改 `update_fundamental_data()` 中的 `batch_size`：

```python
# 每次更新 50 支股票（注意 API rate limit）
batch_size = 50
```

## Cron 表達式參考

| 表達式                                      | 說明          |
| ------------------------------------------- | ------------- |
| `minute=0`                                  | 每小時整點    |
| `hour=16, minute=0`                         | 每日 16:00    |
| `hour=15, minute=30, day_of_week='mon-fri'` | 週一~五 15:30 |
| `hour=18, minute=0, day_of_week='fri'`      | 每週五 18:00  |
| `hour=2, minute=0, day_of_week='sun'`       | 每週日 02:00  |

## 日誌查看

排程器會將日誌輸出至：
- `logs/scheduler.log` - 排程器主日誌
- 終端（stdout）- 即時輸出

查看最近的日誌：

```bash
tail -f logs/scheduler.log
```

查看今天的統計：

```bash
grep "資料更新統計" logs/scheduler.log | tail -1
```

## 監控與告警

### 檢查排程器狀態

```bash
# 檢查進程是否運行
ps aux | grep scheduler.py

# 檢查最後更新時間
tail -10 logs/scheduler.log
```

### 整合監控工具

可以整合 Prometheus + Grafana 或其他監控工具監控排程器健康狀態。

## 故障排除

### 問題 1：排程器無法啟動

**症狀**：`FileNotFoundError: Configuration file not found`

**解決方案**：
```bash
# 確保配置檔案存在
ls -la config/api_keys.json

# 檢查 FinMind token 是否配置
cat config/api_keys.json | grep finmind
```

### 問題 2：任務未執行

**症狀**：到了排程時間但任務沒有執行

**解決方案**：
1. 檢查日誌 `logs/scheduler.log`
2. 確認系統時區設置正確（`Asia/Taipei`）
3. 檢查是否有異常拋出

### 問題 3：API Rate Limit

**症狀**：`RateLimitExceeded` 錯誤

**解決方案**：
- 減少 `batch_size`
- 增加任務間隔時間
- 考慮升級 FinMind API 方案

## 生產環境部署

### 使用 systemd（推薦）

創建服務檔案 `/etc/systemd/system/fingear-scheduler.service`：

```ini
[Unit]
Description=FinGear Data Update Scheduler
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/FinGear
ExecStart=/path/to/venv/bin/python scripts/scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user. target
```

啟用服務：

```bash
sudo systemctl daemon-reload
sudo systemctl enable fingear-scheduler
sudo systemctl start fingear-scheduler
sudo systemctl status fingear-scheduler
```

### 使用 Docker

參考 `docker-compose.yml` 添加 scheduler 服務：

```yaml
scheduler:
  build: .
  command: python scripts/scheduler.py
  volumes:
    - ./data:/app/data
    - ./logs:/app/logs
    - ./config:/app/config
  restart: always
```

## 最佳實踐

1. **定期檢查日誌**：設置日誌輪替，定期檢查錯誤
2. **監控資源使用**：確保伺服器有足夠的記憶體和磁碟空間
3. **備份數據**：定期備份 `data/` 目錄
4. **測試排程**：在生產環境前先在測試環境驗證
5. **版本控制**：排程配置變更應納入版本控制

## 進階功能

### 動態調整排程

可以通過修改代碼實現動態調整排程時間（例如根據市場狀態調整更新頻率）。

### 任務依賴

使用 APScheduler 的任務鏈功能實現任務依賴關係。

### 分散式部署

使用 APScheduler 的分散式後端（如 Redis）實現多節點排程。

---

**版本**: 1.0.0  
**最後更新**: 2026-01-03  
**維護者**: FinGear Team
