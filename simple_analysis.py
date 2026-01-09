#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""簡單分析選股流程"""

from pathlib import Path
import pandas as pd

# 讀取選股結果
csv_path = Path('reports/selections/selections_2026-01-04.csv')
if csv_path.exists():
    df = pd.read_csv(csv_path)
    print(f'=' * 60)
    print(f'最終選股結果分析')
    print(f'=' * 60)
    print(f'總數: {len(df)} 檔')
    print()
    print(df[['symbol', 'fundamental_score', 'chip_score', 'tech_score', 'signal']])
else:
    print("找不到選股報告")

# 讀取 top_stocks.txt 檢查格式
print()
print(f'=' * 60)
print(f'股票池檢查')
print(f'=' * 60)

stocks = []
with open('config/top_stocks.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # 取第一個空格之前的部分作為股票代碼
        symbol = line.split()[0]
        if symbol.isdigit():
            stocks.append(symbol)

print(f'有效股票數: {len(stocks)}')
print(f'前 10 個: {stocks[:10]}')
print()

# 手動分析籌碼面評分
print(f'=' * 60)
print(f'籌碼面評分分析（只分析有數據的股票）')
print(f'=' * 60)

from src.parquet_manager import ParquetManager

data_manager = ParquetManager(Path('data'))

# 從日誌中我們知道這些股票都參與了籌碼面評估
test_symbols = ['2356', '2027', '1229', '8046', '4746', '5269', '6782', '3293', '2207', '8069',
                '1513', '6285', '3036', '3702', '2206', '3529', '2376', '8938', '2812', '2395',
                '9910', '6505', '2886', '2404', '1102', '9933', '3005', '2912', '5434']

chip_results = []
for symbol in test_symbols:
    chip_df = data_manager.read_chip_data(symbol)
    if chip_df.empty or len(chip_df) < 5:
        chip_results.append({
            'symbol': symbol,
            'chip_score': 0,
            'status': '數據不足'
        })
        continue

    recent_5d = chip_df.tail(5)
    chip_score = 0

    # 投信連買
    trust_consecutive = 0
    for i in range(len(recent_5d) - 1, -1, -1):
        if recent_5d.iloc[i]['trust_net'] > 0:
            trust_consecutive += 1
        else:
            break

    if trust_consecutive >= 5:
        chip_score += 30
    elif trust_consecutive >= 3:
        chip_score += 20
    elif trust_consecutive >= 1:
        chip_score += 10

    # 外資
    foreign_5d_avg = recent_5d['foreign_net'].mean()
    foreign_latest = recent_5d.iloc[-1]['foreign_net']

    if foreign_5d_avg > 1000 and foreign_latest > 0:
        chip_score += 25
    elif foreign_5d_avg > 0:
        chip_score += 15
    elif foreign_5d_avg > -1000:
        chip_score += 5

    # 自營
    dealer_5d_total = recent_5d['dealer_net'].sum()
    if dealer_5d_total > 0:
        chip_score += 15
    elif dealer_5d_total > -500:
        chip_score += 8

    # 法人合計
    total_5d_sum = recent_5d['total_net'].sum()
    if total_5d_sum > 5000:
        chip_score += 20
    elif total_5d_sum > 1000:
        chip_score += 15
    elif total_5d_sum > 0:
        chip_score += 10

    # 大戶持股
    share_df = data_manager.read_shareholding_data(symbol)
    if not share_df.empty and len(share_df) >= 2:
        latest_ratio = share_df.iloc[-1]['major_ratio']
        prev_ratio = share_df.iloc[-2]['major_ratio']
        ratio_change = latest_ratio - prev_ratio
        if ratio_change > 0.5:
            chip_score += 10
        elif ratio_change >= 0:
            chip_score += 5

    status = "✅ PASS" if chip_score >= 60 else "❌ FAIL"
    chip_results.append({
        'symbol': symbol,
        'chip_score': chip_score,
        'status': status
    })

result_df = pd.DataFrame(chip_results).sort_values('chip_score', ascending=False)
print(result_df.to_string(index=False))
print()

print(f'=' * 60)
print(f'結論')
print(f'=' * 60)
passed = result_df[result_df['chip_score'] >= 60]
print(f'通過籌碼面（>= 60分）: {len(passed)} 檔')
if len(passed) > 0:
    print(passed[['symbol', 'chip_score']].to_string(index=False))

failed_but_close = result_df[(result_df['chip_score'] >= 50) & (result_df['chip_score'] < 60)]
print(f'\n接近門檻（50-59分）: {len(failed_but_close)} 檔')
if len(failed_but_close) > 0:
    print(failed_but_close[['symbol', 'chip_score']].to_string(index=False))

print(f'\n籌碼面平均分數: {result_df["chip_score"].mean():.1f}')
print(f'籌碼面中位數: {result_df["chip_score"].median():.1f}')
print(f'\n💡 建議: 如果想要更多選股結果，可以考慮：')
print(f'  1. 降低籌碼面門檻（目前 60 分，可調整至 50-55 分）')
print(f'  2. 調整各因子權重（目前投信 30%, 外資 25%, 自營 15%, 合計 20%, 持股 10%）')
