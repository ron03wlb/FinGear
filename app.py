#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FinGear 網頁儀表板 - Flask 後端應用

提供選股結果的 Web API 服務，支援：
- 最新選股數據展示
- 歷史數據查詢
- 個股詳細資訊
"""

from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, date, timedelta
import json
import logging
import ast
import re

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 支援中文 JSON

# 日誌配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 報表目錄
REPORT_DIR = Path('reports/selections')


def get_latest_report_path():
    """獲取最新選股報表路徑"""
    if not REPORT_DIR.exists():
        return None
    
    report_files = list(REPORT_DIR.glob('selections_*.csv'))
    if not report_files:
        return None
    
    return max(report_files)


def parse_selection_data(file_path: Path):
    """解析選股 CSV 數據"""
    try:
        df = pd.read_csv(file_path)

        # 安全解析函數 - 處理包含 numpy 物件的字串
        def safe_eval(x):
            if not isinstance(x, str):
                return {}
            try:
                # 提供 numpy 命名空間給 eval，以便處理 np.float64() 等
                return eval(x, {"__builtins__": {}, "np": np})
            except Exception as e:
                logger.warning(f"無法解析: {x[:100]}... 錯誤: {e}")
                return {}

        # 解析 chip_details、tech_details 與 fundamental_details JSON 字串
        if 'chip_details' in df.columns:
            df['chip_details'] = df['chip_details'].apply(safe_eval)

        if 'tech_details' in df.columns:
            df['tech_details'] = df['tech_details'].apply(safe_eval)

        if 'fundamental_details' in df.columns:
            df['fundamental_details'] = df['fundamental_details'].apply(safe_eval)

        return df
    except Exception as e:
        logger.error(f"解析數據失敗: {e}", exc_info=True)
        return None


@app.route('/')
def index():
    """首頁 - 儀表板"""
    return render_template('index.html')


@app.route('/api/latest')
def get_latest_selection():
    """API: 獲取最新選股數據"""
    latest_file = get_latest_report_path()
    
    if not latest_file:
        return jsonify({'error': '尚無選股數據'}), 404
    
    df = parse_selection_data(latest_file)
    if df is None:
        return jsonify({'error': '數據解析失敗'}), 500
    
    # 提取日期
    date_str = latest_file.stem.replace('selections_', '')
    
    return jsonify({
        'date': date_str,
        'total': len(df),
        'stocks': df.to_dict(orient='records')
    })


@app.route('/api/history')
def get_history_dates():
    """API: 獲取歷史報表日期列表"""
    if not REPORT_DIR.exists():
        return jsonify([])
    
    dates = []
    for file in sorted(REPORT_DIR.glob('selections_*.csv'), reverse=True):
        date_str = file.stem.replace('selections_', '')
        dates.append(date_str)
    
    return jsonify(dates)


@app.route('/api/history/<date_str>')
def get_historical_selection(date_str):
    """API: 獲取指定日期的選股數據"""
    file_path = REPORT_DIR / f'selections_{date_str}.csv'
    
    if not file_path.exists():
        return jsonify({'error': f'{date_str} 無數據'}), 404
    
    df = parse_selection_data(file_path)
    if df is None:
        return jsonify({'error': '數據解析失敗'}), 500
    
    return jsonify({
        'date': date_str,
        'total': len(df),
        'stocks': df.to_dict(orient='records')
    })


@app.route('/api/stock/<symbol>')
def get_stock_detail(symbol):
    """API: 獲取個股詳細資訊（從最新報表）"""
    latest_file = get_latest_report_path()
    
    if not latest_file:
        return jsonify({'error': '尚無選股數據'}), 404
    
    df = parse_selection_data(latest_file)
    if df is None:
        return jsonify({'error': '數據解析失敗'}), 500
    
    # 嘗試將 symbol 轉換為整數進行比對（CSV 中可能是整數類型）
    try:
        symbol_int = int(symbol)
        stock_data = df[df['symbol'] == symbol_int]
    except ValueError:
        stock_data = df[df['symbol'] == symbol]
    
    if stock_data.empty:
        return jsonify({'error': f'找不到股票 {symbol}'}), 404
    
    return jsonify(stock_data.iloc[0].to_dict())


if __name__ == '__main__':
    # 確保模板與靜態資源目錄存在
    Path('templates').mkdir(exist_ok=True)
    Path('static/css').mkdir(parents=True, exist_ok=True)
    Path('static/js').mkdir(parents=True, exist_ok=True)
    
    logger.info("🚀 FinGear 儀表板啟動於 http://localhost:8080")
    app.run(debug=True, host='0.0.0.0', port=8080)

