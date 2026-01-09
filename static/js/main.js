// FinGear 選股儀表板 - 前端邏輯

let currentData = [];
let sortColumn = 'fundamental_score';  // 預設按基本面總分排序
let sortAscending = false;
let stockNames = {}; // 股票名稱對照表

// 頁面載入時初始化
document.addEventListener('DOMContentLoaded', () => {
    loadStockNames();  // 載入股票名稱對照表
    loadHistoryDates();
    loadLatestData();

    // 日期選擇器事件
    document.getElementById('dateSelect').addEventListener('change', (e) => {
        if (e.target.value === 'latest') {
            loadLatestData();
        } else {
            loadHistoricalData(e.target.value);
        }
    });
});

// 載入歷史日期列表
async function loadHistoryDates() {
    try {
        const response = await fetch('/api/history');
        const dates = await response.json();

        const select = document.getElementById('dateSelect');
        dates.forEach(date => {
            const option = document.createElement('option');
            option.value = date;
            option.textContent = date;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('載入歷史日期失敗:', error);
    }
}

// 載入股票名稱對照表
async function loadStockNames() {
    try {
        const response = await fetch('/static/data/stock_names.json');
        stockNames = await response.json();
        console.log('股票名稱載入成功:', stockNames);
    } catch (error) {
        console.error('載入股票名稱失敗:', error);
    }
}

// 根據分數返回顏色樣式
function getScoreColor(score) {
    if (score >= 80) {
        return 'background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600;';
    } else if (score >= 60) {
        return 'background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600;';
    } else if (score >= 40) {
        return 'background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #1f2937; padding: 4px 12px; border-radius: 12px; font-weight: 600;';
    } else {
        return 'background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600;';
    }
}

// 根據數值類型返回顏色
function getValueColor(value, type) {
    if (!value && value !== 0) return '#636e72';

    switch (type) {
        case 'roe': // ROE: 高=綠 (這裡數值是百分比，如 19.3)
            if (value > 15) return '#10b981';
            if (value > 8) return '#3b82f6';
            return '#ef4444';
        case 'growth': // 成長率: 正=綠, 負=紅
            return value > 0 ? '#10b981' : '#ef4444';
        case 'pe': // PE相對: 低=綠（便宜）
            if (value < 0.9) return '#10b981';
            if (value < 1.1) return '#3b82f6';
            return '#ef4444';
        case 'fcf': // FCF: 高=綠
            return value > 0 ? '#10b981' : '#ef4444';
        case 'debt': // 負債: 低=綠 (這裡數值是百分比，如 19.6)
            if (value < 40) return '#10b981';
            if (value < 60) return '#3b82f6';
            return '#ef4444';
        case 'pe': // PE相對 (這裡數值是 Z-score，低於 0 代表低於平均)
            if (value < -1) return '#10b981';
            if (value < 0) return '#3b82f6';
            return '#ef4444';
        default:
            return '#636e72';
    }
}

// 格式化百分比 (數值已是百分比，不需再乘以 100)
function formatPercent(value) {
    if (!value && value !== 0) return '-';
    return `${value.toFixed(1)}%`;
}

// 格式化成長率（帶正負號，數值已是百分比，不需再乘以 100）
function formatGrowth(value) {
    if (!value && value !== 0) return '-';
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}%`;
}

// 格式化 PE 相對值 (Z-Score)
function formatPE(value) {
    if (!value && value !== 0) return '-';
    return value.toFixed(2);
}

// 格式化金額（單位為元，轉為億）
function formatMoney(value) {
    if (!value && value !== 0) return '-';
    return `${(value / 1e8).toFixed(1)}億`;
}

// 翻譯訊號為中文
function translateSignal(signal) {
    const mapping = {
        'STRONG_BUY': '強力買進',
        'BUY': '買進',
        'WATCH': '觀察',
        'HOLD': '持有',
        'REDUCE': '減碼',
        'OVERBOUGHT_REDUCE': '超買減碼',
        'DATA_INSUFFICIENT': '數據不足'
    };
    return mapping[signal] || signal;
}

// 載入最新數據
async function loadLatestData() {
    try {
        const response = await fetch('/api/latest');
        const data = await response.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        updateDisplay(data);
    } catch (error) {
        console.error('載入最新數據失敗:', error);
        alert('載入數據失敗，請檢查後端服務是否啟動');
    }
}

// 載入歷史數據
async function loadHistoricalData(dateStr) {
    try {
        const response = await fetch(`/api/history/${dateStr}`);
        const data = await response.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        updateDisplay(data);
    } catch (error) {
        console.error('載入歷史數據失敗:', error);
    }
}

// 更新頁面顯示
function updateDisplay(data) {
    currentData = data.stocks;

    // 更新統計摘要
    document.getElementById('currentDate').textContent = data.date;
    document.getElementById('totalStocks').textContent = data.total;

    const strongBuyCount = currentData.filter(s => s.signal === 'STRONG_BUY').length;
    document.getElementById('strongBuyCount').textContent = strongBuyCount;

    // 渲染表格
    renderTable();
}

// 渲染表格
function renderTable() {
    const tbody = document.getElementById('stockTableBody');
    tbody.innerHTML = '';

    if (currentData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="loading">無選股數據</td></tr>';
        return;
    }

    // 排序數據
    const sortedData = [...currentData].sort((a, b) => {
        let aVal, bVal;

        // 處理基本面因子的排序
        if (['roe', 'eps_yoy', 'pe_relative', 'fcf', 'gross_margin_trend', 'revenue_yoy', 'debt_ratio'].includes(sortColumn)) {
            const aDetails = a.fundamental_details || {};
            const bDetails = b.fundamental_details || {};
            aVal = aDetails[sortColumn]?.raw_value || 0;
            bVal = bDetails[sortColumn]?.raw_value || 0;
        } else {
            aVal = a[sortColumn] || 0;
            bVal = b[sortColumn] || 0;
        }

        return sortAscending ? aVal - bVal : bVal - aVal;
    });

    // 填充表格
    sortedData.forEach(stock => {
        const row = document.createElement('tr');
        // 優先使用 API 返回的名稱，否則查表
        const stockName = stock.stock_name || stockNames[stock.symbol] || '';
        const fundamentalDetails = stock.fundamental_details || {};

        // 提取各因子原始值
        const roe = fundamentalDetails.roe?.raw_value;
        const peRelative = fundamentalDetails.pe_relative?.raw_value;
        const grossMargin = fundamentalDetails.gross_margin_trend?.raw_value;

        row.innerHTML = `
            <td class="sticky-col">
                <strong>${stock.symbol}</strong>
                ${stockName ? `<br><span style="font-size: 0.85rem; color: #636e72;">${stockName}</span>` : ''}
            </td>
            <td><span class="score-badge" style="${getScoreColor(stock.fundamental_score)}">${Math.round(stock.fundamental_score)}</span></td>
            <td style="color: ${getValueColor(roe, 'roe')}; font-weight: 500;">${formatPercent(roe)}</td>
            <td style="color: ${getValueColor(peRelative, 'pe')}; font-weight: 500;">${formatPE(peRelative)}</td>
            <td style="color: ${getValueColor(grossMargin, 'growth')}; font-weight: 500;">${formatGrowth(grossMargin)}</td>
            <td><span class="score-badge" style="${getScoreColor(stock.chip_score)}">${Math.round(stock.chip_score)}</span></td>
            <td><span class="score-badge" style="${getScoreColor(stock.tech_score)}">${Math.round(stock.tech_score)}</span></td>
            <td><span class="signal-badge signal-${stock.signal}">${translateSignal(stock.signal)}</span></td>
            <td><button class="detail-btn" onclick="showStockDetail('${stock.symbol}')">詳情</button></td>
        `;
        tbody.appendChild(row);
    });
}

// 表格排序
function sortTable(column) {
    if (sortColumn === column) {
        sortAscending = !sortAscending;
    } else {
        sortColumn = column;
        sortAscending = false;
    }
    renderTable();
}

// 顯示個股詳細資訊
async function showStockDetail(symbol) {
    try {
        const response = await fetch(`/api/stock/${symbol}`);
        const stock = await response.json();

        if (stock.error) {
            alert(stock.error);
            return;
        }

        renderStockDetail(stock);
        document.getElementById('stockModal').style.display = 'block';
    } catch (error) {
        console.error('載入個股詳情失敗:', error);
    }
}

// 渲染個股詳細資訊
function renderStockDetail(stock) {
    const modalBody = document.getElementById('modalBody');
    const stockName = stock.stock_name || stockNames[stock.symbol] || '';

    // 解析詳細數據
    const chipDetails = stock.chip_details || {};
    const techDetails = stock.tech_details || {};
    const fundamentalDetails = stock.fundamental_details || {};

    modalBody.innerHTML = `
        <h2>${stock.symbol} ${stockName} - 選股詳細分析</h2>

        <!-- 三維度分數 -->
        <div class="score-card">
            <div class="score-item">
                <h3>基本面</h3>
                <div class="score">${Math.round(stock.fundamental_score)}</div>
            </div>
            <div class="score-item">
                <h3>籌碼面</h3>
                <div class="score">${Math.round(stock.chip_score)}</div>
            </div>
            <div class="score-item">
                <h3>技術面</h3>
                <div class="score">${Math.round(stock.tech_score)}</div>
            </div>
        </div>

        <!-- 基本面詳情 -->
        ${Object.keys(fundamentalDetails).length > 0 ? `
        <div class="detail-section">
            <h3>💰 基本面分析</h3>
            <div class="detail-grid">
                ${Object.entries(fundamentalDetails).map(([key, data]) => {
        const score = data.score || 0;
        const weight = (data.weight * 100).toFixed(0);
        const weighted = (data.weighted || 0).toFixed(2);
        return `
                        <div class="detail-item">
                            <span class="label">${translateFundamentalKey(key)}</span>
                            <span class="value">
                                評分: ${score}/5
                                <span style="color: #636e72; font-size: 0.9em;">
                                    (權重${weight}% = ${weighted}分)
                                </span>
                            </span>
                        </div>
                    `;
    }).join('')}
            </div>
        </div>
        ` : ''}

        <!-- 籌碼面詳情 -->
        <div class="detail-section">
            <h3>📊 籌碼面分析</h3>
            <div class="detail-grid">
                ${Object.entries(chipDetails).map(([key, value]) => `
                    <div class="detail-item">
                        <span class="label">${translateChipKey(key)}</span>
                        <span class="value">${value}</span>
                    </div>
                `).join('')}
            </div>
        </div>

        <!-- 技術面詳情 -->
        <div class="detail-section">
            <h3>📈 技術面分析</h3>
            <div class="detail-grid">
                ${Object.entries(techDetails).map(([key, value]) => `
                    <div class="detail-item">
                        <span class="label">${translateTechKey(key)}</span>
                        <span class="value">${value}</span>
                    </div>
                `).join('')}
            </div>
        </div>

        <!-- 綜合訊號 -->
        <div class="detail-section">
            <h3>🎯 綜合訊號</h3>
            <div style="text-align: center; padding: 20px;">
                <span class="signal-badge signal-${stock.signal}" style="font-size: 1.5rem; padding: 12px 24px;">
                    ${stock.signal}
                </span>
            </div>
        </div>
    `;
}

// 翻譯基本面欄位名稱
function translateFundamentalKey(key) {
    const mapping = {
        'pe_relative': 'PE 相對估值',
        'roe': 'ROE 股東權益報酬率',
        'eps_yoy': 'EPS 年增率',
        'fcf': '自由現金流',
        'gross_margin_trend': '毛利率趨勢',
        'revenue_yoy': '營收年增率',
        'debt_ratio': '負債比率'
    };
    return mapping[key] || key;
}

// 翻譯籌碼欄位名稱
function translateChipKey(key) {
    const mapping = {
        'trust_days': '投信連買天數',
        'foreign_status': '外資態度',
        'dealer_status': '自營商動向',
        'total_strength': '法人合計強度',
        'share_trend': '大戶持股趨勢'
    };
    return mapping[key] || key;
}

// 翻譯技術欄位名稱
function translateTechKey(key) {
    const mapping = {
        'ma_trend': '均線趨勢',
        'bias_60': '季線乖離率',
        'macd': 'MACD 動能',
        'rsi': 'RSI 指標',
        'kd': 'KD 指標',
        'volume': '量能狀態',
        'bbands': '布林通道位置'
    };
    return mapping[key] || key;
}

// 關閉 Modal
function closeModal() {
    document.getElementById('stockModal').style.display = 'none';
}

// 點擊外部關閉 Modal
window.onclick = function (event) {
    const modal = document.getElementById('stockModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}
