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
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import requests
import base64

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
    
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return {
        "stocks": results,
        "timestamp": now,
        "source": "Yahoo Finance"
    }


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


# 종목 검색용 데이터베이스
STOCK_DATABASE = [
    # 한국 주요 종목
    {"symbol": "005930.KS", "name": "삼성전자", "keywords": "samsung electronics 삼전"},
    {"symbol": "000660.KS", "name": "SK하이닉스", "keywords": "sk hynix 하이닉스"},
    {"symbol": "035420.KS", "name": "NAVER", "keywords": "네이버 naver"},
    {"symbol": "035720.KS", "name": "카카오", "keywords": "kakao"},
    {"symbol": "006400.KS", "name": "삼성SDI", "keywords": "samsung sdi 삼성에스디아이"},
    {"symbol": "051910.KS", "name": "LG화학", "keywords": "lg chem 엘지화학"},
    {"symbol": "373220.KS", "name": "LG에너지솔루션", "keywords": "lg energy solution 엘지에너지"},
    {"symbol": "005380.KS", "name": "현대차", "keywords": "hyundai motor 현대자동차"},
    {"symbol": "000270.KS", "name": "기아", "keywords": "kia 기아차"},
    {"symbol": "068270.KS", "name": "셀트리온", "keywords": "celltrion"},
    {"symbol": "207940.KS", "name": "삼성바이오로직스", "keywords": "samsung biologics 삼바"},
    {"symbol": "003670.KS", "name": "포스코퓨처엠", "keywords": "posco future m 포스코"},
    {"symbol": "028260.KS", "name": "삼성물산", "keywords": "samsung c&t 삼성건설"},
    {"symbol": "018260.KS", "name": "삼성에스디에스", "keywords": "samsung sds 삼성SDS"},
    {"symbol": "009150.KS", "name": "삼성전기", "keywords": "samsung electro-mechanics"},
    {"symbol": "066570.KS", "name": "LG전자", "keywords": "lg electronics 엘지전자"},
    {"symbol": "003550.KS", "name": "LG", "keywords": "lg corp 엘지"},
    {"symbol": "105560.KS", "name": "KB금융", "keywords": "kb financial 국민은행"},
    {"symbol": "055550.KS", "name": "신한지주", "keywords": "shinhan 신한은행"},
    {"symbol": "086790.KS", "name": "하나금융지주", "keywords": "hana financial 하나은행"},
    # 미국 주요 종목
    {"symbol": "AAPL", "name": "Apple", "keywords": "애플 아이폰 iphone"},
    {"symbol": "MSFT", "name": "Microsoft", "keywords": "마이크로소프트 윈도우"},
    {"symbol": "GOOGL", "name": "Alphabet (Google)", "keywords": "구글 알파벳 youtube"},
    {"symbol": "AMZN", "name": "Amazon", "keywords": "아마존 aws"},
    {"symbol": "NVDA", "name": "NVIDIA", "keywords": "엔비디아 GPU 그래픽"},
    {"symbol": "META", "name": "Meta (Facebook)", "keywords": "메타 페이스북 인스타그램"},
    {"symbol": "TSLA", "name": "Tesla", "keywords": "테슬라 전기차"},
    {"symbol": "AMD", "name": "AMD", "keywords": "에이엠디 라이젠"},
    {"symbol": "INTC", "name": "Intel", "keywords": "인텔 cpu"},
    {"symbol": "NFLX", "name": "Netflix", "keywords": "넷플릭스"},
    {"symbol": "DIS", "name": "Disney", "keywords": "디즈니"},
    {"symbol": "JPM", "name": "JPMorgan Chase", "keywords": "제이피모건"},
    {"symbol": "V", "name": "Visa", "keywords": "비자"},
    {"symbol": "MA", "name": "Mastercard", "keywords": "마스터카드"},
    {"symbol": "BAC", "name": "Bank of America", "keywords": "뱅크오브아메리카"},
    {"symbol": "GS", "name": "Goldman Sachs", "keywords": "골드만삭스"},
    {"symbol": "UNH", "name": "UnitedHealth", "keywords": "유나이티드헬스"},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "keywords": "존슨앤존슨"},
    {"symbol": "PFE", "name": "Pfizer", "keywords": "화이자"},
    {"symbol": "LLY", "name": "Eli Lilly", "keywords": "일라이릴리"},
    {"symbol": "XOM", "name": "ExxonMobil", "keywords": "엑슨모빌"},
    {"symbol": "CVX", "name": "Chevron", "keywords": "쉐브론"},
    {"symbol": "KO", "name": "Coca-Cola", "keywords": "코카콜라"},
    {"symbol": "PEP", "name": "PepsiCo", "keywords": "펩시콜라"},
    {"symbol": "MCD", "name": "McDonald's", "keywords": "맥도날드"},
    {"symbol": "SBUX", "name": "Starbucks", "keywords": "스타벅스"},
    {"symbol": "NKE", "name": "Nike", "keywords": "나이키"},
    {"symbol": "BA", "name": "Boeing", "keywords": "보잉"},
    {"symbol": "CAT", "name": "Caterpillar", "keywords": "캐터필러"},
    # ETF
    {"symbol": "SPY", "name": "S&P 500 ETF", "keywords": "sp500 에스피"},
    {"symbol": "QQQ", "name": "Nasdaq 100 ETF", "keywords": "나스닥 큐큐큐"},
    {"symbol": "GLD", "name": "Gold ETF", "keywords": "금 골드"},
    {"symbol": "SLV", "name": "Silver ETF", "keywords": "은 실버"},
    {"symbol": "USO", "name": "Oil ETF", "keywords": "원유 오일"},
]


@app.get("/api/search")
async def search_ticker(q: str):
    """종목 검색 API"""
    if not q or len(q) < 1:
        return {"results": []}
    
    query = q.lower()
    results = []
    
    for stock in STOCK_DATABASE:
        # 심볼, 이름, 키워드에서 검색
        if (query in stock["symbol"].lower() or 
            query in stock["name"].lower() or 
            query in stock.get("keywords", "").lower()):
            results.append({
                "symbol": stock["symbol"],
                "name": stock["name"]
            })
    
    return {"results": results[:10]}


@app.get("/api/heatmap")
async def heatmap_data():
    """히트맵용 주요 종목 데이터 API"""
    # 히트맵에 표시할 주요 종목 리스트
    heatmap_tickers = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD",
        "JPM", "V", "MA", "UNH", "JNJ", "LLY", "XOM", "AVGO",
        "005930.KS", "000660.KS", "035420.KS", "035720.KS", "005380.KS"
    ]
    
    def fetch_change(ticker):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            # regularMarketChangePercent 또는 trailingPegRatio 등은 실시간성에 따라 다를 수 있음
            # 간단하게 previousClose와 currentPrice 비교
            current = info.get("currentPrice") or info.get("regularMarketPrice")
            prev = info.get("regularMarketPreviousClose")
            
            if current and prev:
                change = ((current - prev) / prev) * 100
                return {
                    "ticker": ticker,
                    "name": info.get("shortName") or ticker,
                    "change": round(change, 2),
                    "price": current,
                    "marketCap": info.get("marketCap", 0)
                }
        except:
            return None
        return None

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_change, t): t for t in heatmap_tickers}
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
    
    return {"results": results}


@app.get("/api/macro")
async def macro_data():
    """FRED 및 주요 글로벌 매크로 지표 (10종 패키지)"""
    indicators = {
        "^TNX": {
            "name": "미 10년물 국채 금리", 
            "desc": "경제의 '기준 금리'. 모든 대출과 주식 가치 평가의 출발점입니다.",
            "link": "https://finance.yahoo.com/quote/%5ETNX"
        },
        "10Y2Y": {
            "name": "장단기 금리차 (10Y-2Y)", 
            "desc": "침체 예보관. 0 이하(역전)로 내려가면 1~2년 내 경기 침체가 온다는 강력한 신호입니다.",
            "link": "https://fred.stlouisfed.org/series/T10Y2Y"
        },
        "WALCL": {
            "name": "연준 총자산 (Money Print)", 
            "desc": "연준이 찍어낸 돈의 총량. 그래프가 내려가면 시장에서 돈을 회수(긴축)하고 있다는 뜻입니다.",
            "link": "https://fred.stlouisfed.org/series/WALCL"
        },
        "RRPONTSYD": {
            "name": "역래포 잔액 (Liquidity)", 
            "desc": "시장의 '남는 돈' 저장고. 이 수치가 줄어들면 시중에 유동성이 공급되고 있다는 긍정적 신호입니다.",
            "link": "https://fred.stlouisfed.org/series/RRPONTSYD"
        },
        "T10YIE": {
            "name": "10년 기대인플레이션", 
            "desc": "시장이 예상하는 미래 물가. 2%를 크게 상회하면 금리 인하가 어려워집니다.",
            "link": "https://fred.stlouisfed.org/series/T10YIE"
        },
        "HYG": {
            "name": "하이일드 채권 (Risk On/Off)", 
            "desc": "부실 기업들의 채권 가격. 그래프가 꺾이면 기업들의 자금난과 경기 하강이 시작됐음을 의미합니다.",
            "link": "https://finance.yahoo.com/quote/HYG"
        },
        "DX-Y.NYB": {
            "name": "달러 인덱스 (DXY)", 
            "desc": "글로벌 달러 파워. 상승 시 한국 등 신흥국 주식 시장에는 보통 악재로 작용합니다.",
            "link": "https://finance.yahoo.com/quote/DX-Y.NYB"
        },
        "^VIX": {
            "name": "공포 지수 (CBOE VIX)", 
            "desc": "투자자들의 불안 지수. 보통 20~30을 넘어가면 시장이 패닉 상태임을 뜻합니다.",
            "link": "https://finance.yahoo.com/quote/%5EVIX"
        },
        "GC=F": {
            "name": "금 선물 (Gold)", 
            "desc": "최종 안전 자산. 화폐 가치가 떨어지거나 전쟁 등 위기 시 가격이 치솟습니다.",
            "link": "https://finance.yahoo.com/quote/GC=F"
        },
        "CL=F": {
            "name": "서부 텍사스유 (WTI)", 
            "desc": "에너지 물가. 유가가 너무 높으면 소비가 위축되고 물가가 올라 경제에 부담을 줍니다.",
            "link": "https://finance.yahoo.com/quote/CL=F"
        },
    }

    def fetch_indicator(symbol, info):
        try:
            # 특수 계산 지표 처리
            if symbol == "10Y2Y":
                t10 = yf.Ticker("^TNX").history(period="6mo")
                t2 = yf.Ticker("^IRX").history(period="6mo")
                if not t10.empty and not t2.empty:
                    df = t10['Close'] - t2['Close']
                    df = df.dropna()
                    current, prev = df.iloc[-1], df.iloc[-2]
                    chart_data = [{"time": t.strftime("%Y-%m-%d"), "value": round(v, 3)} for t, v in df.items()]
                    return {
                        "symbol": symbol, "name": info["name"], "desc": info["desc"],
                        "link": info["link"],
                        "value": round(current, 3), "change": round(current - prev, 3),
                        "chart_data": chart_data[-120:]
                    }
            
            # FRED 또는 일반 지표
            stock = yf.Ticker(symbol)
            hist = stock.history(period="6mo")
            if hist.empty:
                # 일부 FRED 지표는 Yahoo에서 종종 누락되므로 일반 대행 지표 사용 로직 필요 (여기서는 yfinance 지원 전제)
                return None

            current, prev = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            change = ((current - prev) / prev) * 100
            chart_data = [{"time": t.strftime("%Y-%m-%d"), "value": round(v, 2)} for t, v in hist['Close'].items()]
            
            return {
                "symbol": symbol, "name": info["name"], "desc": info["desc"],
                "link": info["link"],
                "value": round(current, 2), "change": round(change, 2),
                "chart_data": chart_data[-120:]
            }
        except: return None

    target_symbols = list(indicators.keys())
    results = []
    with ThreadPoolExecutor(max_workers=len(target_symbols)) as executor:
        futures = {executor.submit(fetch_indicator, s, indicators[s]): s for s in target_symbols}
        for future in as_completed(futures):
            res = future.result()
            if res: results.append(res)
    
    # 순서 유지
    ordered = [r for s in target_symbols for r in results if r['symbol'] == s]
    return {"results": ordered}


@app.get("/api/fwd-per")
@app.get("/api/valuation")
async def valuation_data(tickers: str):
    """밸류에이션 데이터 API - PER, PBR, PSR, EV/EBITDA, 배당수익률, ROE"""
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    
    if not ticker_list:
        return {"stocks": []}
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def fetch_valuation(ticker):
        """개별 종목 밸류에이션 데이터 가져오기"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            name = info.get("shortName") or info.get("longName") or ticker
            price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
            market_cap = info.get("marketCap", 0)
            sector = info.get("sector", "")
            
            # PER
            trailing_pe = info.get("trailingPE")
            forward_pe = info.get("forwardPE")
            trailing_eps = info.get("trailingEps")
            forward_eps = info.get("forwardEps")
            
            # PBR (Price to Book)
            pbr = info.get("priceToBook")
            book_value = info.get("bookValue")
            
            # PSR (Price to Sales)
            psr = info.get("priceToSalesTrailing12Months")
            revenue_per_share = info.get("revenuePerShare")
            
            # EV/EBITDA
            ev = info.get("enterpriseValue")
            ebitda = info.get("ebitda")
            ev_ebitda = None
            if ev and ebitda and ebitda > 0:
                ev_ebitda = ev / ebitda
            
            # 배당수익률
            dividend_yield = info.get("dividendYield")
            # yfinance info의 dividendYield는 이미 퍼센트 단위(0.34 = 0.34%)인 경우가 많음
            # 단, trailingAnnualDividendYield 등은 소수점(0.0034)인 경우가 있어 혼동 주의
            # 여기서는 API가 제공하는 원시값을 그대로 사용하여 정교함을 유지함
            
            # ROE
            roe = info.get("returnOnEquity")
            if roe is not None:
                roe = roe * 100 # ROE는 소수점 단위(0.15 = 15%)로 제공됨
            
            # 영업이익률
            operating_margin = info.get("operatingMargins")
            if operating_margin is not None:
                operating_margin = operating_margin * 100 # 소수점 단위 (0.21 = 21%)
            
            return {
                "ticker": ticker,
                "name": name,
                "price": round(price, 2) if price else 0,
                "marketCap": market_cap,
                "sector": sector,
                # PER
                "trailingPE": round(trailing_pe, 2) if trailing_pe else None,
                "forwardPE": round(forward_pe, 2) if forward_pe else None,
                "trailingEPS": round(trailing_eps, 2) if trailing_eps else None,
                "forwardEPS": round(forward_eps, 2) if forward_eps else None,
                # PBR
                "pbr": round(pbr, 2) if pbr else None,
                "bookValue": round(book_value, 2) if book_value else None,
                # PSR
                "psr": round(psr, 2) if psr else None,
                # EV/EBITDA
                "evEbitda": round(ev_ebitda, 2) if ev_ebitda else None,
                # 배당
                "dividendYield": round(dividend_yield, 2) if dividend_yield else None,
                # 수익성
                "roe": round(roe, 2) if roe else None,
                "operatingMargin": round(operating_margin, 2) if operating_margin else None,
            }
        except Exception as e:
            print(f"Valuation Error: {ticker} - {e}")
            return None
    
    # 병렬 처리 (최대 10개)
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_valuation, t): t for t in ticker_list[:20]}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
    
    # 입력 순서 유지
    ordered = []
    for t in ticker_list:
        for r in results:
            if r["ticker"].upper() == t.upper():
                ordered.append(r)
                break
    
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "stocks": ordered,
        "timestamp": now,
        "source": "Yahoo Finance"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
