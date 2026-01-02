// FinGear 選股儀表板 - 前端邏輯

let currentData = [];
let sortColumn = 'tech_score';
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
        tbody.innerHTML = '<tr><td colspan="6" class="loading">無選股數據</td></tr>';
        return;
    }

    // 排序數據
    const sortedData = [...currentData].sort((a, b) => {
        const aVal = a[sortColumn] || 0;
        const bVal = b[sortColumn] || 0;
        return sortAscending ? aVal - bVal : bVal - aVal;
    });

    // 填充表格
    sortedData.forEach(stock => {
        const row = document.createElement('tr');
        const stockName = stockNames[stock.symbol] || '';
        row.innerHTML = `
            <td>
                <strong>${stock.symbol}</strong>
                ${stockName ? `<br><span style="font-size: 0.85rem; color: #636e72;">${stockName}</span>` : ''}
            </td>
            <td><span class="score-badge" style="${getScoreColor(stock.fundamental_score)}">${Math.round(stock.fundamental_score)}</span></td>
            <td><span class="score-badge" style="${getScoreColor(stock.chip_score)}">${Math.round(stock.chip_score)}</span></td>
            <td><span class="score-badge" style="${getScoreColor(stock.tech_score)}">${Math.round(stock.tech_score)}</span></td>
            <td><span class="signal-badge signal-${stock.signal}">${stock.signal}</span></td>
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
    const stockName = stockNames[stock.symbol] || '';

    // 解析詳細數據
    const chipDetails = stock.chip_details || {};
    const techDetails = stock.tech_details || {};

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
