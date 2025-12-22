/**
 * 토스 미니앱 - 차트 로직 (개선)
 * 섹터별 선택, 날짜 선택 기능 추가
 */

let chart = null;
let series = {};
let selectedTickers = ['AAPL', 'NVDA'];
let currentPeriod = '1mo';
let customDateRange = null;

// 토스 색상 팔레트
const COLORS = ['#3182F6', '#00C853', '#FF5252', '#FF9800', '#9C27B0', '#00BCD4'];

// 차트 옵션
const chartOptions = {
    layout: {
        background: { type: 'solid', color: '#FFFFFF' },
        textColor: '#191F28',
        fontFamily: 'Pretendard, sans-serif',
    },
    grid: {
        vertLines: { color: '#E5E8EB' },
        horzLines: { color: '#E5E8EB' },
    },
    crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: { color: '#8B95A1', width: 1, style: 2 },
        horzLine: { color: '#8B95A1', width: 1, style: 2 },
    },
    rightPriceScale: { borderColor: '#E5E8EB' },
    timeScale: { borderColor: '#E5E8EB', timeVisible: true },
    handleScroll: { mouseWheel: false, horzTouchDrag: true, vertTouchDrag: false },
    handleScale: { mouseWheel: false, pinch: false },
};

// 차트 초기화
function initChart() {
    const container = document.getElementById('chart-container');

    chart = LightweightCharts.createChart(container, {
        ...chartOptions,
        width: container.clientWidth,
        height: 260,
    });

    window.addEventListener('resize', () => {
        chart.resize(container.clientWidth, 260);
    });

    // 날짜 기본값 설정
    setDefaultDates();

    updateTags();
    loadData();
}

// 날짜 기본값
function setDefaultDates() {
    const today = new Date();
    const monthAgo = new Date();
    monthAgo.setMonth(today.getMonth() - 1);

    document.getElementById('end-date').value = today.toISOString().split('T')[0];
    document.getElementById('start-date').value = monthAgo.toISOString().split('T')[0];
}

// 티커 추가
function addTicker(ticker) {
    ticker = ticker.toUpperCase().trim();
    if (!ticker || selectedTickers.includes(ticker)) return;
    if (selectedTickers.length >= 6) {
        alert('최대 6개까지 추가할 수 있어요');
        return;
    }

    selectedTickers.push(ticker);
    updateTags();
    loadData();
    document.getElementById('ticker-input').value = '';
}

// 티커 제거
function removeTicker(ticker) {
    selectedTickers = selectedTickers.filter(t => t !== ticker);
    if (series[ticker]) {
        try { chart.removeSeries(series[ticker]); } catch (e) { }
        delete series[ticker];
    }
    updateTags();
    loadData();
}

// 태그 업데이트
function updateTags() {
    const container = document.getElementById('ticker-tags');
    container.innerHTML = '';

    selectedTickers.forEach((ticker, i) => {
        const tag = document.createElement('div');
        tag.className = 'ticker-tag';
        tag.innerHTML = `
            <span class="tag-dot" style="background:${COLORS[i % COLORS.length]}"></span>
            <span class="tag-name">${ticker}</span>
            <button class="tag-remove" onclick="removeTicker('${ticker}')">×</button>
        `;
        container.appendChild(tag);
    });
}

// 데이터 로드
async function loadData() {
    if (!selectedTickers.length) {
        updateLegend([]);
        return;
    }

    showLoading(true);

    try {
        let url = `/api/compare?tickers=${selectedTickers.join(',')}&period=${currentPeriod}&_t=${Date.now()}`;

        // 커스텀 날짜 범위가 있으면 추가
        if (customDateRange) {
            url += `&start=${customDateRange.start}&end=${customDateRange.end}`;
        }

        const res = await fetch(url, { cache: 'no-store' });
        const data = await res.json();

        if (data.error) {
            showLoading(false);
            return;
        }

        // 기존 시리즈 제거
        Object.keys(series).forEach(t => {
            try { chart.removeSeries(series[t]); } catch (e) { }
        });
        series = {};

        // 새 시리즈 추가
        data.stocks.forEach((stock, i) => {
            const s = chart.addLineSeries({
                color: COLORS[i % COLORS.length],
                lineWidth: 2,
                priceLineVisible: false,
            });
            s.setData(stock.data);
            series[stock.ticker] = s;
        });

        chart.timeScale().fitContent();
        updateLegend(data.stocks);

    } catch (e) {
        console.error(e);
    } finally {
        showLoading(false);
    }
}

// 범례 업데이트
function updateLegend(stocks) {
    const container = document.getElementById('legend');
    container.innerHTML = '';

    stocks.forEach((stock, i) => {
        const isUp = stock.return >= 0;
        const item = document.createElement('div');
        item.className = 'legend-item';
        item.innerHTML = `
            <span class="legend-dot" style="background:${COLORS[i % COLORS.length]}"></span>
            <span class="legend-name">${stock.ticker}</span>
            <span class="legend-value ${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}${stock.return}%</span>
        `;
        container.appendChild(item);
    });
}

// 로딩
function showLoading(show) {
    document.getElementById('loading').classList.toggle('hidden', !show);
}

// 이벤트 리스너
document.addEventListener('DOMContentLoaded', () => {
    initChart();

    // 기간 선택 칩
    document.querySelectorAll('.period-chip').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.period-chip').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentPeriod = btn.dataset.period;
            customDateRange = null;  // 커스텀 날짜 초기화
            loadData();
        });
    });

    // 추가 버튼
    document.getElementById('add-btn').addEventListener('click', () => {
        addTicker(document.getElementById('ticker-input').value);
    });

    // 엔터 키
    document.getElementById('ticker-input').addEventListener('keypress', e => {
        if (e.key === 'Enter') addTicker(e.target.value);
    });

    // 날짜 적용 버튼
    document.getElementById('apply-date-btn').addEventListener('click', () => {
        const start = document.getElementById('start-date').value;
        const end = document.getElementById('end-date').value;

        if (start && end) {
            customDateRange = { start, end };
            // 기간 칩 선택 해제
            document.querySelectorAll('.period-chip').forEach(b => b.classList.remove('active'));
            loadData();
        }
    });
});
