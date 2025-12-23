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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
