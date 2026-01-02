FROM python:3.9-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements.txt .

# 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案文件
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY config/ ./config/

# 建立數據目錄
RUN mkdir -p /data/daily /data/history /data/fundamentals /data/chips /reports /logs

# 設定環境變數
ENV PYTHONPATH=/app
ENV TZ=Asia/Taipei

# 設定 Cron Job
COPY crontab /etc/cron.d/fingear-cron
RUN chmod 0644 /etc/cron.d/fingear-cron
RUN crontab /etc/cron.d/fingear-cron

# 啟動 Cron 服務
CMD ["cron", "-f"]
