"""
토스 미니앱 - 주식 비교 차트
FastAPI 서버 (토스 가이드라인 준수)
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf

app = FastAPI(title="주식 비교 차트", version="1.0.0")

# CORS 설정 - 토스 앱인토스 도메인 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://chartview.apps.tossmini.com",        # 실제 서비스 환경
        "https://chartview.private-apps.tossmini.com", # 콘솔 QR 테스트 환경
        "*",  # 개발용 (프로덕션에서는 제거 권장)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 및 템플릿
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/compare")
async def compare_stocks(tickers: str, period: str = "1mo", start: str = None, end: str = None):
    """여러 종목 비교 API (날짜 범위 지원)"""
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    
    if not ticker_list:
        return JSONResponse({"error": "종목을 입력해주세요"}, status_code=400)
    
    # 기간별 인터벌
    interval_map = {
        "1d": "5m", "5d": "15m", "1mo": "1h",
        "3mo": "1d", "6mo": "1d", "1y": "1d", "max": "1d"
    }
    interval = interval_map.get(period, "1d")
    
    results = []
    
    for ticker in ticker_list[:6]:
        try:
            stock = yf.Ticker(ticker)
            
            # 날짜 범위가 있으면 사용, 없으면 기간 사용
            if start and end:
                df = stock.history(start=start, end=end, interval="1d")
            else:
                df = stock.history(period=period, interval=interval)
            
            if df.empty:
                continue
            
            info = stock.info
            name = info.get("shortName", ticker)
            
            # 수익률 계산
            first = df["Close"].iloc[0]
            line_data = []
            
            for idx, row in df.iterrows():
                pct = ((row["Close"] - first) / first) * 100
                line_data.append({
                    "time": int(idx.timestamp()),
                    "value": round(pct, 2)
                })
            
            current = round(df["Close"].iloc[-1], 2)
            total = round(((df["Close"].iloc[-1] - first) / first) * 100, 2)
            
            results.append({
                "ticker": ticker,
                "name": name,
                "price": current,
                "return": total,
                "data": line_data
            })
            
        except Exception as e:
            print(f"Error: {ticker} - {e}")
            continue
    
    return {"stocks": results}


@app.get("/api/popular")
async def popular():
    """인기 종목"""
    return {
        "us": [
            {"symbol": "AAPL", "name": "Apple"},
            {"symbol": "MSFT", "name": "Microsoft"},
            {"symbol": "GOOGL", "name": "Google"},
            {"symbol": "NVDA", "name": "NVIDIA"},
            {"symbol": "TSLA", "name": "Tesla"},
            {"symbol": "AMZN", "name": "Amazon"},
        ],
        "kr": [
            {"symbol": "005930.KS", "name": "삼성전자"},
            {"symbol": "000660.KS", "name": "SK하이닉스"},
            {"symbol": "035420.KS", "name": "NAVER"},
            {"symbol": "035720.KS", "name": "카카오"},
        ]
    }


@app.get("/api/heatmap")
async def heatmap_data(tickers: str, period: str = "1d"):
    """히트맵 데이터 API - 종목별 변동률"""
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    
    if not ticker_list:
        return {"stocks": []}
    
    # 기간 매핑 (1일은 5일 데이터를 가져와서 마지막 2일 비교)
    period_map = {
        "1d": "5d",   # 1일 변동은 5일치 데이터에서 마지막 2일 비교
        "1w": "1mo",  # 1주 변동
        "1mo": "3mo", # 1개월 변동
        "3mo": "6mo"  # 3개월 변동
    }
    yf_period = period_map.get(period, "5d")
    
    results = []
    
    for ticker in ticker_list[:50]:  # 최대 50개
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=yf_period)
            
            if df.empty or len(df) < 2:
                continue
            
            # 기간에 따른 변동률 계산
            if period == "1d":
                # 1일: 전일 종가 vs 오늘 종가
                prev_close = df["Close"].iloc[-2]
                last_close = df["Close"].iloc[-1]
            else:
                # 다른 기간: 첫날 vs 마지막날
                days_map = {"1w": 5, "1mo": 21, "3mo": 63}
                days = days_map.get(period, 5)
                idx = min(days, len(df) - 1)
                prev_close = df["Close"].iloc[-idx-1] if len(df) > idx else df["Close"].iloc[0]
                last_close = df["Close"].iloc[-1]
            
            change = ((last_close - prev_close) / prev_close) * 100
            
            results.append({
                "ticker": ticker,
                "price": round(last_close, 2),
                "change": round(change, 2)
            })
            
        except Exception as e:
            print(f"Heatmap Error: {ticker} - {e}")
            continue
    
    return {"stocks": results}


@app.get("/api/heatmap-full")
async def heatmap_full_data(tickers: str, period: str = "1d"):
    """Finviz 스타일 히트맵 - 병렬 처리로 빠른 로딩"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    
    if not ticker_list:
        return {"stocks": []}
    
    # 기간 매핑
    period_map = {
        "1d": "5d",
        "1w": "1mo",
        "1mo": "3mo",
        "3mo": "6mo"
    }
    yf_period = period_map.get(period, "5d")
    
    def fetch_stock_data(ticker):
        """개별 종목 데이터 가져오기"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            df = stock.history(period=yf_period)
            
            if df.empty or len(df) < 2:
                return None
            
            # 변동률 계산
            if period == "1d":
                prev_close = df["Close"].iloc[-2]
                last_close = df["Close"].iloc[-1]
            else:
                days_map = {"1w": 5, "1mo": 21, "3mo": 63}
                days = days_map.get(period, 5)
                idx = min(days, len(df) - 1)
                prev_close = df["Close"].iloc[-idx-1] if len(df) > idx else df["Close"].iloc[0]
                last_close = df["Close"].iloc[-1]
            
            change = ((last_close - prev_close) / prev_close) * 100
            
            # 시가총액, P/E, Forward P/E 가져오기
            market_cap = info.get("marketCap", 0)
            pe_ratio = info.get("trailingPE")
            fwd_pe_ratio = info.get("forwardPE")
            
            return {
                "ticker": ticker,
                "price": round(last_close, 2),
                "change": round(change, 2),
                "marketCap": market_cap,
                "pe": round(pe_ratio, 2) if pe_ratio else None,
                "fwdPe": round(fwd_pe_ratio, 2) if fwd_pe_ratio else None
            }
            
        except Exception as e:
            print(f"Heatmap Error: {ticker} - {e}")
            return None
    
    # 병렬 처리 (최대 20개 스레드)
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_stock_data, ticker): ticker for ticker in ticker_list[:160]}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
    
    return {"stocks": results}


# S&P 500 섹터별 종목 (전체)
SECTOR_STOCKS = {
    'Technology': [
        'AAPL', 'MSFT', 'NVDA', 'AVGO', 'ORCL', 'CRM', 'ADBE', 'AMD', 'INTC', 'CSCO',
        'IBM', 'QCOM', 'TXN', 'NOW', 'INTU', 'AMAT', 'MU', 'LRCX', 'KLAC', 'SNPS',
        'CDNS', 'ADSK', 'ADI', 'FTNT', 'PANW', 'ANSS', 'MPWR', 'KEYS', 'NXPI', 'MCHP',
        'ON', 'FSLR', 'HPQ', 'HPE', 'WDC', 'STX', 'NTAP', 'JNPR', 'AKAM', 'ZBRA',
        'EPAM', 'IT', 'CTSH', 'GDDY', 'GEN', 'FFIV', 'SWKS', 'QRVO', 'TER', 'ENPH'
    ],
    'Communication': [
        'GOOGL', 'GOOG', 'META', 'NFLX', 'DIS', 'CMCSA', 'VZ', 'T', 'TMUS', 'CHTR',
        'EA', 'WBD', 'PARA', 'FOXA', 'FOX', 'OMC', 'IPG', 'TTWO', 'LYV', 'MTCH',
        'NWS', 'NWSA', 'DISH'
    ],
    'Consumer Cyclical': [
        'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'LOW', 'TJX', 'BKNG', 'CMG',
        'ORLY', 'AZO', 'ROST', 'MAR', 'HLT', 'DHI', 'LEN', 'PHM', 'NVR', 'GM',
        'F', 'APTV', 'EBAY', 'ETSY', 'DPZ', 'YUM', 'DARDEN', 'POOL', 'BBY', 'ULTA',
        'LVS', 'WYNN', 'MGM', 'CZR', 'RCL', 'CCL', 'NCLH', 'EXPE', 'GRMN', 'BWA',
        'RL', 'TPR', 'PVH', 'VFC', 'HAS', 'LEG', 'MHK', 'WHR'
    ],
    'Financial': [
        'BRK-B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'AXP', 'BLK',
        'C', 'SCHW', 'CB', 'PGR', 'MMC', 'ICE', 'CME', 'AON', 'MET', 'AIG',
        'TRV', 'PNC', 'USB', 'TFC', 'AMP', 'SPGI', 'MCO', 'MSCI', 'FIS', 'FISV',
        'COF', 'BK', 'STT', 'NTRS', 'FITB', 'KEY', 'RF', 'CFG', 'HBAN', 'ZION',
        'MTB', 'CINF', 'L', 'ALL', 'AFL', 'PRU', 'LNC', 'GL', 'AIZ', 'BRO',
        'WRB', 'RE', 'HIG', 'CNA', 'ALLY', 'SYF', 'DFS', 'NDAQ', 'CBOE', 'IVZ'
    ],
    'Healthcare': [
        'UNH', 'LLY', 'JNJ', 'ABBV', 'MRK', 'PFE', 'TMO', 'ABT', 'DHR', 'BMY',
        'AMGN', 'MDT', 'CVS', 'ELV', 'ISRG', 'GILD', 'VRTX', 'SYK', 'HCA', 'CI',
        'ZTS', 'BDX', 'BSX', 'REGN', 'MCK', 'COR', 'EW', 'IQV', 'IDXX', 'HUM',
        'DXCM', 'A', 'MTD', 'BAX', 'WST', 'CAH', 'RMD', 'HOLX', 'TFX', 'DGX',
        'VTRS', 'MOH', 'CNC', 'ALGN', 'COO', 'TECH', 'LH', 'PKI', 'BIO', 'HSIC',
        'XRAY', 'CTLT', 'OGN', 'INCY', 'BIIB'
    ],
    'Industrials': [
        'GE', 'CAT', 'RTX', 'HON', 'UNP', 'BA', 'UPS', 'DE', 'LMT', 'MMM',
        'ETN', 'ADP', 'ITW', 'WM', 'EMR', 'GD', 'CSX', 'NSC', 'PH', 'TT',
        'NOC', 'CTAS', 'JCI', 'PCAR', 'CARR', 'OTIS', 'ROK', 'CMI', 'FDX', 'TDG',
        'FAST', 'AME', 'LHX', 'GWW', 'VRSK', 'IR', 'PWR', 'XYL', 'DOV', 'WAB',
        'SWK', 'IEX', 'HUBB', 'CSGP', 'LDOS', 'J', 'BAH', 'CPRT', 'EXPD', 'UAL',
        'DAL', 'LUV', 'ALK', 'AAL', 'CHRW', 'JBHT', 'ODFL', 'GNRC', 'MAS', 'ALLE'
    ],
    'Consumer Defensive': [
        'PG', 'KO', 'PEP', 'COST', 'WMT', 'PM', 'MO', 'CL', 'MDLZ', 'KHC',
        'EL', 'STZ', 'GIS', 'SYY', 'KMB', 'K', 'HSY', 'KR', 'CLX', 'TAP',
        'TSN', 'CAG', 'ADM', 'BG', 'SJM', 'MKC', 'CPB', 'HRL', 'CHD', 'WBA',
        'DG', 'DLTR', 'TGT'
    ],
    'Energy': [
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL',
        'DVN', 'PXD', 'HES', 'WMB', 'KMI', 'OKE', 'FANG', 'BKR', 'TRGP', 'CTRA',
        'MRO', 'APA', 'EQT'
    ],
    'Real Estate': [
        'PLD', 'AMT', 'EQIX', 'CCI', 'PSA', 'SPG', 'WELL', 'DLR', 'O', 'AVB',
        'EQR', 'ARE', 'ESS', 'MAA', 'UDR', 'VTR', 'WY', 'SBAC', 'EXR', 'INVH',
        'VICI', 'IRM', 'KIM', 'REG', 'CPT', 'HST', 'BXP', 'PEAK', 'SLG', 'FRT'
    ],
    'Utilities': [
        'NEE', 'DUK', 'SO', 'D', 'AEP', 'SRE', 'EXC', 'XEL', 'WEC', 'ES',
        'ED', 'AWK', 'EIX', 'DTE', 'ETR', 'FE', 'PCG', 'AEE', 'LNT', 'CMS',
        'CNP', 'NI', 'PNW', 'ATO', 'EVRG', 'NRG', 'PPL'
    ],
    'Materials': [
        'LIN', 'APD', 'SHW', 'FCX', 'NEM', 'ECL', 'DD', 'NUE', 'DOW', 'CTVA',
        'VMC', 'MLM', 'PPG', 'ALB', 'IFF', 'CE', 'CF', 'MOS', 'FMC', 'EMN',
        'AVY', 'IP', 'PKG', 'SEE', 'WRK', 'BALL', 'AMCR'
    ]
}

# 서버 캐시 (5분간 유효)
import time
heatmap_cache = {}
CACHE_DURATION = 300  # 5분

@app.get("/api/heatmap-cached")
async def heatmap_cached(period: str = "1d"):
    """캐시된 히트맵 데이터 (빠른 로딩)"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # 캐시 확인
    cache_key = f"heatmap_{period}"
    if cache_key in heatmap_cache:
        cached_data, cached_time = heatmap_cache[cache_key]
        if time.time() - cached_time < CACHE_DURATION:
            return cached_data
    
    period_map = {"1d": "5d", "1w": "1mo", "1mo": "3mo", "3mo": "1y"}
    yf_period = period_map.get(period, "1mo")
    
    def fetch_stock(ticker):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            df = stock.history(period=yf_period)
            
            if df.empty or len(df) < 2:
                return None
            
            last_close = df["Close"].iloc[-1]
            
            # 기간에 따른 비교 시점 결정
            if period == "1d":
                # 1일: 어제 종가와 비교
                prev_close = df["Close"].iloc[-2] if len(df) >= 2 else df["Close"].iloc[0]
            elif period == "1w":
                # 1주: 약 5거래일 전
                idx = min(5, len(df) - 1)
                prev_close = df["Close"].iloc[-idx-1] if len(df) > idx else df["Close"].iloc[0]
            elif period == "1mo":
                # 1개월: 약 21거래일 전
                idx = min(21, len(df) - 1)
                prev_close = df["Close"].iloc[-idx-1] if len(df) > idx else df["Close"].iloc[0]
            else:
                # 3개월: 약 63거래일 전
                idx = min(63, len(df) - 1)
                prev_close = df["Close"].iloc[-idx-1] if len(df) > idx else df["Close"].iloc[0]
            
            change = ((last_close - prev_close) / prev_close) * 100
            
            return {
                "ticker": ticker,
                "price": round(last_close, 2),
                "change": round(change, 2),
                "marketCap": info.get("marketCap", 1e9),
                "pe": round(info.get("trailingPE", 0), 1) if info.get("trailingPE") else None,
                "fwdPe": round(info.get("forwardPE", 0), 1) if info.get("forwardPE") else None
            }
        except:
            return None
    
    # 병렬 처리 (50개 스레드)
    all_tickers = [t for tickers in SECTOR_STOCKS.values() for t in tickers]
    stock_data = {}
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(fetch_stock, t): t for t in all_tickers}
        for future in as_completed(futures):
            result = future.result()
            if result:
                stock_data[result["ticker"]] = result
    
    # 섹터별로 그룹화
    sectors = []
    for sector_name, tickers in SECTOR_STOCKS.items():
        stocks = [stock_data[t] for t in tickers if t in stock_data]
        if stocks:
            stocks.sort(key=lambda x: x.get("marketCap", 0), reverse=True)
            sectors.append({"name": sector_name, "stocks": stocks})
    
    # 전체 시가총액 기준 정렬
    sectors.sort(key=lambda x: sum(s.get("marketCap", 0) for s in x["stocks"]), reverse=True)
    
    result = {"sectors": sectors}
    
    # 캐시 저장
    heatmap_cache[cache_key] = (result, time.time())
    
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)



