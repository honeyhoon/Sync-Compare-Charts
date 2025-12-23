/**
 * Finviz 스타일 히트맵 - D3.js Treemap
 */

document.addEventListener('DOMContentLoaded', function () {
    let heatmapCache = null;
    let currentHeatmapPeriod = '1d';
    let currentMetric = 'change';

    // 탭 전환
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            const tabContent = document.getElementById(this.dataset.tab + '-tab');
            if (tabContent) tabContent.classList.add('active');
            if (this.dataset.tab === 'heatmap') loadHeatmap();
        });
    });

    // 기간 선택
    document.querySelectorAll('.heatmap-period-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.heatmap-period-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentHeatmapPeriod = this.dataset.period;
            heatmapCache = null;
            loadHeatmap();
        });
    });

    // 지표 선택
    document.querySelectorAll('.metric-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.metric-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentMetric = this.dataset.metric;
            if (heatmapCache) renderTreemap(heatmapCache);
        });
    });

    // 히트맵 로드
    async function loadHeatmap() {
        const container = document.getElementById('heatmap-grid');
        if (!container) return;

        if (heatmapCache) {
            renderTreemap(heatmapCache);
            return;
        }

        container.innerHTML = '<div class="heatmap-loading">📊 S&P 500 로딩 중...</div>';

        try {
            const res = await fetch(`/api/heatmap-cached?period=${currentHeatmapPeriod}`);
            const data = await res.json();
            if (data.sectors && data.sectors.length > 0) {
                heatmapCache = data;
                renderTreemap(data);
            } else {
                container.innerHTML = '<div class="heatmap-empty">데이터 없음</div>';
            }
        } catch (e) {
            console.error(e);
            container.innerHTML = '<div class="heatmap-empty">오류</div>';
        }
    }

    // D3.js Treemap 렌더링
    function renderTreemap(data) {
        const container = document.getElementById('heatmap-grid');
        container.innerHTML = '';

        const width = container.clientWidth || window.innerWidth;
        const height = Math.max(500, window.innerHeight - 300);

        // 계층 데이터 생성
        const hierarchy = {
            name: "S&P 500",
            children: data.sectors.map(sector => ({
                name: sector.name,
                children: sector.stocks.map(stock => ({
                    name: stock.ticker,
                    value: stock.marketCap || 1e9,
                    data: stock
                }))
            }))
        };

        // D3 계층 구조
        const root = d3.hierarchy(hierarchy)
            .sum(d => d.value)
            .sort((a, b) => b.value - a.value);

        // Treemap 레이아웃
        d3.treemap()
            .size([width, height])
            .paddingTop(15)
            .paddingRight(1)
            .paddingBottom(1)
            .paddingLeft(1)
            .paddingInner(1)
            .round(true)
            (root);

        // SVG 생성
        const svg = d3.create("svg")
            .attr("width", width)
            .attr("height", height)
            .style("font-family", "Arial, sans-serif");

        // 섹터 그룹 (depth 1)
        const sectors = svg.selectAll("g.sector")
            .data(root.children)
            .join("g")
            .attr("class", "sector");

        // 섹터 헤더 배경 (클릭 가능)
        sectors.append("rect")
            .attr("x", d => d.x0)
            .attr("y", d => d.y0)
            .attr("width", d => d.x1 - d.x0)
            .attr("height", 15)
            .attr("fill", "#1a1d21")
            .style("cursor", "pointer")
            .on("click", (event, d) => {
                event.stopPropagation();
                showSectorList(d.data.name, d.children.map(c => c.data.data));
            });

        // 섹터 헤더 텍스트
        sectors.append("text")
            .attr("x", d => d.x0 + 3)
            .attr("y", d => d.y0 + 11)
            .attr("fill", "#888")
            .attr("font-size", "9px")
            .attr("font-weight", "bold")
            .style("pointer-events", "none")
            .text(d => d.data.name.toUpperCase());

        // 개별 종목 (depth 2 - leaves)
        const leaves = svg.selectAll("g.leaf")
            .data(root.leaves())
            .join("g")
            .attr("class", "leaf")
            .attr("transform", d => `translate(${d.x0},${d.y0})`)
            .style("cursor", "pointer")
            .on("click", (event, d) => showStockDetail(d.data.data));

        // 셀 배경
        leaves.append("rect")
            .attr("width", d => Math.max(0, d.x1 - d.x0))
            .attr("height", d => Math.max(0, d.y1 - d.y0))
            .attr("fill", d => getColor(d.data.data))
            .attr("stroke", "#0a0a0a")
            .attr("stroke-width", 0.5)
            .on("mouseenter", function () { d3.select(this).attr("stroke", "#fff"); })
            .on("mouseleave", function () { d3.select(this).attr("stroke", "#0a0a0a"); });

        // 티커 텍스트
        leaves.append("text")
            .attr("x", d => (d.x1 - d.x0) / 2)
            .attr("y", d => (d.y1 - d.y0) / 2 - ((d.y1 - d.y0 > 35) ? 5 : 0))
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .attr("fill", "#fff")
            .attr("font-weight", "bold")
            .attr("font-size", d => Math.min(12, (d.x1 - d.x0) / 4) + "px")
            .text(d => {
                const w = d.x1 - d.x0;
                const h = d.y1 - d.y0;
                return (w > 20 && h > 15) ? d.data.name : "";
            });

        // 변동률 텍스트
        leaves.append("text")
            .attr("x", d => (d.x1 - d.x0) / 2)
            .attr("y", d => (d.y1 - d.y0) / 2 + 8)
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .attr("fill", "#fff")
            .attr("font-size", d => Math.min(9, (d.x1 - d.x0) / 5) + "px")
            .text(d => {
                const w = d.x1 - d.x0;
                const h = d.y1 - d.y0;
                if (w < 30 || h < 35) return "";
                return getDisplayValue(d.data.data);
            });

        container.appendChild(svg.node());
    }

    // 상세 팝업
    function showStockDetail(stock) {
        const existingPopup = document.getElementById('stock-popup');
        if (existingPopup) existingPopup.remove();

        const popup = document.createElement('div');
        popup.id = 'stock-popup';
        popup.className = 'stock-popup';

        const changeClass = (stock.change || 0) >= 0 ? 'up' : 'down';
        const changeSign = (stock.change || 0) >= 0 ? '+' : '';

        popup.innerHTML = `
            <div class="popup-header">
                <span class="popup-ticker">${stock.ticker}</span>
                <button class="popup-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
            <div class="popup-content">
                <div class="popup-row">
                    <span class="popup-label">현재가</span>
                    <span class="popup-value">$${stock.price}</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">변동률</span>
                    <span class="popup-value ${changeClass}">${changeSign}${(stock.change || 0).toFixed(2)}%</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">시가총액</span>
                    <span class="popup-value">${formatMarketCap(stock.marketCap)}</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">P/E</span>
                    <span class="popup-value">${stock.pe ? stock.pe.toFixed(1) : 'N/A'}</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">FWD P/E</span>
                    <span class="popup-value">${stock.fwdPe ? stock.fwdPe.toFixed(1) : 'N/A'}</span>
                </div>
            </div>
            <button class="popup-chart-btn" onclick="document.querySelector('.tab-btn[data-tab=\\'chart\\']').click(); if(typeof addTicker==='function') addTicker('${stock.ticker}'); this.parentElement.remove();">
                📈 차트에 추가
            </button>
        `;

        document.body.appendChild(popup);

        setTimeout(() => {
            document.addEventListener('click', function closePopup(e) {
                if (!popup.contains(e.target)) {
                    popup.remove();
                    document.removeEventListener('click', closePopup);
                }
            });
        }, 100);
    }

    function formatMarketCap(cap) {
        if (!cap) return 'N/A';
        if (cap >= 1e12) return '$' + (cap / 1e12).toFixed(2) + 'T';
        if (cap >= 1e9) return '$' + (cap / 1e9).toFixed(1) + 'B';
        return '$' + (cap / 1e6).toFixed(0) + 'M';
    }

    // 섹터 종목 리스트 모달
    function showSectorList(sectorName, stocks) {
        const existingModal = document.getElementById('sector-list-modal');
        if (existingModal) existingModal.remove();

        const modal = document.createElement('div');
        modal.id = 'sector-list-modal';
        modal.className = 'sector-list-modal';

        const stockRows = stocks.map(stock => {
            const changeClass = (stock.change || 0) >= 0 ? 'up' : 'down';
            const changeSign = (stock.change || 0) >= 0 ? '+' : '';
            return `
                <div class="sector-list-row" onclick="document.getElementById('sector-list-modal').remove(); if(typeof addTicker==='function') { document.querySelector('.tab-btn[data-tab=\\'chart\\']').click(); addTicker('${stock.ticker}'); }">
                    <span class="sl-ticker">${stock.ticker}</span>
                    <span class="sl-price">$${stock.price}</span>
                    <span class="sl-change ${changeClass}">${changeSign}${(stock.change || 0).toFixed(2)}%</span>
                    <span class="sl-cap">${formatMarketCap(stock.marketCap)}</span>
                </div>
            `;
        }).join('');

        modal.innerHTML = `
            <div class="sector-list-header">
                <span class="sector-list-title">${sectorName}</span>
                <button class="sector-list-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
            <div class="sector-list-subheader">
                <span>티커</span>
                <span>가격</span>
                <span>변동률</span>
                <span>시가총액</span>
            </div>
            <div class="sector-list-body">
                ${stockRows}
            </div>
        `;

        document.body.appendChild(modal);

        // 바깥 클릭 시 닫기
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    function getDisplayValue(stock) {
        if (currentMetric === 'pe') return stock.pe ? stock.pe.toFixed(1) : '-';
        if (currentMetric === 'fwdPe') return stock.fwdPe ? stock.fwdPe.toFixed(1) : '-';
        const c = stock.change || 0;
        return (c >= 0 ? '+' : '') + c.toFixed(2) + '%';
    }

    function getColor(stock) {
        const value = currentMetric === 'change' ? (stock.change || 0) :
            currentMetric === 'pe' ? (stock.pe || 20) - 20 : (stock.fwdPe || 20) - 20;

        if (currentMetric !== 'change') {
            if (value < -10) return '#30cc5a';
            if (value < -5) return '#2f9e4f';
            if (value < 0) return '#35764e';
            if (value < 5) return '#414554';
            if (value < 10) return '#8b3e3e';
            return '#f23645';
        }

        if (value >= 3) return '#30cc5a';
        if (value >= 2) return '#2f9e4f';
        if (value >= 1) return '#2d8346';
        if (value >= 0.5) return '#35764e';
        if (value >= 0) return '#414554';
        if (value >= -0.5) return '#4d3a3e';
        if (value >= -1) return '#8b3e3e';
        if (value >= -2) return '#bf3939';
        return '#f23645';
    }
});
