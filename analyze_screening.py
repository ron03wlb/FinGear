#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分析選股流程各階段數據"""

from src.screener import StockScreener
from src.factors import FactorEngine
from src.parquet_manager import ParquetManager
from pathlib import Path
import pandas as pd

# 初始化
data_manager = ParquetManager(Path('data'))
factor_engine = FactorEngine(data_manager)
screener = StockScreener(factor_engine, data_manager)

# 讀取 Top 500 股票池
with open('config/top_stocks.txt', 'r') as f:
    universe = [line.strip() for line in f if line.strip()]

print(f'=' * 60)
print(f'初始股票池: {len(universe)} 檔')
print(f'=' * 60)
print()

# Layer 1: 基本面篩選
print('=' * 60)
print('Layer 1: 基本面篩選（前 30 名 + PE 位階過濾）')
print('=' * 60)

l1_candidates = screener._layer1_fundamental_screen(universe)
print(f'通過 Layer 1: {len(l1_candidates)} 檔')
print()
print('Top 10 基本面得分:')
print(l1_candidates.head(10)[['symbol', 'fundamental_score', 'pe_score']].to_string(index=False))
print()

# Layer 2: 籌碼面篩選
print('=' * 60)
print('Layer 2: 籌碼面篩選（需 >= 60 分）')
print('=' * 60)

# 手動計算每檔股票的籌碼面評分
chip_analysis = []
for _, row in l1_candidates.iterrows():
    symbol = row['symbol']

    chip_score = 0
    chip_details = {}

    # 1. 籌碼數據載入
    chip_df = data_manager.read_chip_data(symbol)
    if chip_df.empty or len(chip_df) < 5:
        chip_analysis.append({
            'symbol': symbol,
            'fundamental_score': row['fundamental_score'],
            'chip_score': 0,
            'status': '數據不足',
            'details': '籌碼數據 < 5 天'
        })
        continue

    recent_5d = chip_df.tail(5)

    # === 因子 1: 投信連續買超天數 (0-30 分) ===
    trust_consecutive = 0
    for i in range(len(recent_5d) - 1, -1, -1):
        if recent_5d.iloc[i]['trust_net'] > 0:
            trust_consecutive += 1
        else:
            break

    if trust_consecutive >= 5:
        chip_score += 30
        chip_details['trust'] = f"{trust_consecutive}連買(30分)"
    elif trust_consecutive >= 3:
        chip_score += 20
        chip_details['trust'] = f"{trust_consecutive}連買(20分)"
    elif trust_consecutive >= 1:
        chip_score += 10
        chip_details['trust'] = f"{trust_consecutive}連買(10分)"
    else:
        chip_details['trust'] = "未買超(0分)"

    # === 因子 2: 外資持倉態度 (0-25 分) ===
    foreign_5d_avg = recent_5d['foreign_net'].mean()
    foreign_latest = recent_5d.iloc[-1]['foreign_net']

    if foreign_5d_avg > 1000 and foreign_latest > 0:
        chip_score += 25
        chip_details['foreign'] = "積極買超(25分)"
    elif foreign_5d_avg > 0:
        chip_score += 15
        chip_details['foreign'] = "溫和買超(15分)"
    elif foreign_5d_avg > -1000:
        chip_score += 5
        chip_details['foreign'] = "小賣(5分)"
    else:
        chip_details['foreign'] = "大賣(0分)"

    # === 因子 3: 自營商動向 (0-15 分) ===
    dealer_5d_total = recent_5d['dealer_net'].sum()
    if dealer_5d_total > 0:
        chip_score += 15
        chip_details['dealer'] = "買超(15分)"
    elif dealer_5d_total > -500:
        chip_score += 8
        chip_details['dealer'] = "中立(8分)"
    else:
        chip_details['dealer'] = "賣超(0分)"

    # === 因子 4: 三大法人合計強度 (0-20 分) ===
    total_5d_sum = recent_5d['total_net'].sum()
    if total_5d_sum > 5000:
        chip_score += 20
        chip_details['total'] = "強勁(20分)"
    elif total_5d_sum > 1000:
        chip_score += 15
        chip_details['total'] = "穩健(15分)"
    elif total_5d_sum > 0:
        chip_score += 10
        chip_details['total'] = "微弱(10分)"
    else:
        chip_details['total'] = "負值(0分)"

    # === 因子 5: 大戶持股趨勢 (0-10 分) ===
    share_df = data_manager.read_shareholding_data(symbol)
    if not share_df.empty and len(share_df) >= 2:
        latest_ratio = share_df.iloc[-1]['major_ratio']
        prev_ratio = share_df.iloc[-2]['major_ratio']
        ratio_change = latest_ratio - prev_ratio

        if ratio_change > 0.5:
            chip_score += 10
            chip_details['share'] = f"+{ratio_change:.2f}%(10分)"
        elif ratio_change >= 0:
            chip_score += 5
            chip_details['share'] = f"+{ratio_change:.2f}%(5分)"
        else:
            chip_details['share'] = f"{ratio_change:.2f}%(0分)"
    else:
        chip_details['share'] = "無數據(0分)"

    status = "PASS" if chip_score >= 60 else "FAIL"

    chip_analysis.append({
        'symbol': symbol,
        'fundamental_score': row['fundamental_score'],
        'chip_score': chip_score,
        'status': status,
        'trust': chip_details.get('trust', ''),
        'foreign': chip_details.get('foreign', ''),
        'dealer': chip_details.get('dealer', ''),
        'total': chip_details.get('total', ''),
        'share': chip_details.get('share', '')
    })

chip_df = pd.DataFrame(chip_analysis).sort_values('chip_score', ascending=False)

print(f'通過 Layer 2 (>= 60分): {len(chip_df[chip_df["chip_score"] >= 60])} 檔')
print()
print('籌碼面評分排名 (Top 15):')
print(chip_df.head(15)[['symbol', 'fundamental_score', 'chip_score', 'status']].to_string(index=False))
print()

print('=' * 60)
print('籌碼面詳細分析 (Top 10)')
print('=' * 60)
for idx, row in chip_df.head(10).iterrows():
    print(f"\n{row['symbol']} - 籌碼分數: {row['chip_score']}/100 ({row['status']})")
    print(f"  投信: {row['trust']}")
    print(f"  外資: {row['foreign']}")
    print(f"  自營: {row['dealer']}")
    print(f"  法人合計: {row['total']}")
    print(f"  大戶持股: {row['share']}")

print()
print('=' * 60)
print('結論')
print('=' * 60)
passed = chip_df[chip_df['chip_score'] >= 60]
if len(passed) > 0:
    print(f'✅ 通過籌碼面篩選: {len(passed)} 檔')
    print(passed[['symbol', 'chip_score']].to_string(index=False))
else:
    print('❌ 無股票通過籌碼面篩選')
    print('\n建議：考慮降低籌碼面門檻（目前為 60 分）')
