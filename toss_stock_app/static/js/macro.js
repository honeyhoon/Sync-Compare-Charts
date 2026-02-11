/**
 * 경제 지표 (Macro Insight) 로직
 */

// fwdper.js에서 switchTab을 통해 통합 관리하므로 별도 리스너 제거
document.addEventListener('DOMContentLoaded', () => {
    // 초기 로딩이 필요하다면 여기서 호출 가능하지만, 
    // 기본적으로 탭 클릭 시에만 로드하도록 기획됨
});

async function loadMacroData() {
    const grid = document.getElementById('macro-grid');
    if (!grid) return;

    grid.innerHTML = '<div class="macro-loading-inner"><div class="spinner"></div><p>글로벌 경제 데이터를 번역하고 있습니다...</p></div>';

    try {
        const res = await fetch('/api/macro');
        const data = await res.json();

        if (data.results && data.results.length > 0) {
            renderMacroGrid(data.results);
        } else {
            grid.innerHTML = '<div class="macro-error">데이터를 불러오지 못했습니다.</div>';
        }
    } catch (e) {
        console.error('Macro load error:', e);
        grid.innerHTML = '<div class="macro-error">서버 연결에 실패했습니다.</div>';
    }
}

function renderMacroGrid(indicators) {
    const grid = document.getElementById('macro-grid');
    grid.innerHTML = '';

    indicators.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'macro-card';
        card.style.cursor = 'pointer';

        card.addEventListener('click', () => {
            if (item.link) window.open(item.link, '_blank');
        });

        const isError = item.error === true;
        const isUp = !isError && item.change > 0;
        const colorClass = isError ? 'neutral' : (isUp ? 'up' : 'down');
        const sign = isUp ? '+' : '';
        const chartId = `macro-chart-${index}`;

        const valueDisplay = isError ? 'N/A' : item.value.toLocaleString();
        const changeDisplay = isError ? '-' : `${sign}${item.change}%`;

        // 날짜 정보: 에러가 없고 차트 데이터가 있을 때만
        const hasChart = !isError && item.chart_data && item.chart_data.length > 0;
        const startDate = hasChart ? item.chart_data[0].time : '';
        const endDate = hasChart ? item.chart_data[item.chart_data.length - 1].time : '';

        card.innerHTML = `
            <div class="mc-header">
                <span class="mc-name">${item.name} <span class="link-icon">↗</span></span>
                <span class="mc-symbol">${item.symbol}</span>
            </div>
            <div class="mc-value-row">
                <span class="mc-value">${valueDisplay}</span>
                <span class="mc-change ${colorClass}">${changeDisplay}</span>
            </div>
            <div class="mc-chart-wrapper">
                <div id="${chartId}" class="mc-mini-chart">
                    ${!hasChart ? '<div class="no-chart">데이터 수집 실패</div>' : ''}
                </div>
                ${hasChart ? `
                <div class="mc-chart-dates">
                    <span>${startDate}</span>
                    <span>${endDate}</span>
                </div>` : ''}
            </div>
            <div class="mc-desc">${item.desc}</div>
        `;

        grid.appendChild(card);

        // 미니 차트 생성
        if (hasChart) {
            setTimeout(() => {
                const chartContainer = document.getElementById(chartId);
                if (!chartContainer) return;

                const chart = LightweightCharts.createChart(chartContainer, {
                    width: chartContainer.clientWidth,
                    height: 80,
                    layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#999' },
                    grid: { vertLines: { visible: false }, horzLines: { visible: false } },
                    rightPriceScale: { visible: false },
                    timeScale: { visible: false, borderVisible: false },
                    handleScroll: false,
                    handleScale: false,
                });

                // 지표별 차트 색상 결정 (VIX나 인플레 등 불안하면 빨강, 국채 등은 변동성에 따름)
                let lineColor = isUp ? '#F04452' : '#3182F6';
                if (item.symbol === '^VIX' || item.symbol === 'T10YIE') {
                    lineColor = item.value > 20 || item.change > 0 ? '#F04452' : '#3182F6';
                }

                const lineSeries = chart.addLineSeries({
                    color: lineColor,
                    lineWidth: 2,
                    priceLineVisible: false,
                    crosshairMarkerVisible: false,
                });

                lineSeries.setData(item.chart_data);
                chart.timeScale().fitContent();

                window.addEventListener('resize', () => {
                    if (chartContainer.clientWidth > 0) {
                        chart.resize(chartContainer.clientWidth, 80);
                        chart.timeScale().fitContent();
                    }
                });
            }, 50);
        }
    });
}
