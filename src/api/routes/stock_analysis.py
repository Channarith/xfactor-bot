"""
Stock Analysis API Routes

Comprehensive stock analysis with historical data, fundamentals, technicals,
and inflection point detection for investment decision support.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import logging
import numpy as np

logger = logging.getLogger(__name__)


def to_python_type(val):
    """Convert numpy types to Python native types for JSON serialization."""
    if val is None:
        return None
    if isinstance(val, (np.integer, np.int64, np.int32)):
        return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)):
        return float(val)
    if isinstance(val, (np.bool_, np.bool)):
        return bool(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    return val

router = APIRouter(prefix="/stock-analysis", tags=["stock-analysis"])


# ============================================================================
# Models
# ============================================================================
class PricePoint(BaseModel):
    """Single price data point."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None


class FundamentalDataPoint(BaseModel):
    """Fundamental metric at a point in time."""
    date: str
    value: float


class InflectionPoint(BaseModel):
    """Detected inflection point in price series."""
    date: str
    price: float
    type: str  # 'peak', 'trough', 'crossover_up', 'crossover_down'
    magnitude: float  # Percentage change from previous point
    description: str


class EarningsEvent(BaseModel):
    """Earnings report data."""
    date: str
    reported_eps: Optional[float] = None
    estimated_eps: Optional[float] = None
    surprise_pct: Optional[float] = None
    reported_revenue: Optional[float] = None
    estimated_revenue: Optional[float] = None


class DividendEvent(BaseModel):
    """Dividend payment data."""
    date: str
    amount: float
    yield_pct: Optional[float] = None


class AnalystEstimate(BaseModel):
    """Future analyst estimate."""
    date: str
    estimate_type: str  # 'eps', 'revenue', 'price_target'
    low: float
    mean: float
    high: float
    num_analysts: int


class CompanyMetrics(BaseModel):
    """Current company metrics snapshot."""
    symbol: str
    name: str
    sector: str
    industry: str
    current_price: float
    market_cap: float
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    price_to_book: Optional[float] = None
    price_to_sales: Optional[float] = None
    enterprise_value: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    beta: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    avg_volume: Optional[int] = None
    shares_outstanding: Optional[int] = None
    float_shares: Optional[int] = None
    dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None
    employees: Optional[int] = None


class StockAnalysisResponse(BaseModel):
    """Complete stock analysis response."""
    symbol: str
    company: CompanyMetrics
    price_history: List[PricePoint]
    
    # Fundamental time series
    pe_ratio_history: List[FundamentalDataPoint]
    eps_history: List[FundamentalDataPoint]
    market_cap_history: List[FundamentalDataPoint]
    revenue_history: List[FundamentalDataPoint]
    profit_margin_history: List[FundamentalDataPoint]
    employee_count_history: List[FundamentalDataPoint]
    
    # Technical indicators
    sma_20: List[FundamentalDataPoint]
    sma_50: List[FundamentalDataPoint]
    sma_100: List[FundamentalDataPoint]
    sma_200: List[FundamentalDataPoint]
    ema_12: List[FundamentalDataPoint]
    ema_26: List[FundamentalDataPoint]
    rsi_14: List[FundamentalDataPoint]
    volume_sma_20: List[FundamentalDataPoint]
    
    # Events
    earnings_history: List[EarningsEvent]
    dividend_history: List[DividendEvent]
    
    # Analysis
    inflection_points: List[InflectionPoint]
    
    # Projections
    analyst_estimates: List[AnalystEstimate]
    price_targets: Dict[str, float]  # low, mean, high, current
    
    # Meeting targets analysis
    target_analysis: Dict[str, Any]


# ============================================================================
# Helper Functions
# ============================================================================
def calculate_sma(prices: List[float], period: int) -> List[Optional[float]]:
    """Calculate Simple Moving Average."""
    result = [None] * len(prices)
    for i in range(period - 1, len(prices)):
        result[i] = sum(prices[i - period + 1:i + 1]) / period
    return result


def calculate_ema(prices: List[float], period: int) -> List[Optional[float]]:
    """Calculate Exponential Moving Average."""
    if len(prices) < period:
        return [None] * len(prices)
    
    result = [None] * len(prices)
    multiplier = 2 / (period + 1)
    
    # Start with SMA
    result[period - 1] = sum(prices[:period]) / period
    
    for i in range(period, len(prices)):
        result[i] = (prices[i] - result[i - 1]) * multiplier + result[i - 1]
    
    return result


def calculate_rsi(prices: List[float], period: int = 14) -> List[Optional[float]]:
    """Calculate Relative Strength Index."""
    if len(prices) < period + 1:
        return [None] * len(prices)
    
    result = [None] * len(prices)
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    
    for i in range(period, len(prices)):
        gains = [d if d > 0 else 0 for d in deltas[i - period:i]]
        losses = [-d if d < 0 else 0 for d in deltas[i - period:i]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            result[i] = 100
        else:
            rs = avg_gain / avg_loss
            result[i] = 100 - (100 / (1 + rs))
    
    return result


def detect_inflection_points(
    dates: List[str], 
    prices: List[float], 
    sma_20: List[Optional[float]],
    sma_50: List[Optional[float]],
    threshold_pct: float = 5.0
) -> List[InflectionPoint]:
    """
    Detect inflection points in price series:
    - Local peaks and troughs
    - SMA crossovers (golden cross, death cross)
    """
    inflections = []
    
    if len(prices) < 5:
        return inflections
    
    # Detect local peaks and troughs with minimum magnitude
    for i in range(2, len(prices) - 2):
        # Local peak
        if (prices[i] > prices[i-1] and prices[i] > prices[i-2] and
            prices[i] > prices[i+1] and prices[i] > prices[i+2]):
            
            # Find previous trough
            prev_min = min(prices[max(0, i-20):i])
            magnitude = ((prices[i] - prev_min) / prev_min) * 100 if prev_min > 0 else 0
            
            if magnitude >= threshold_pct:
                inflections.append(InflectionPoint(
                    date=dates[i],
                    price=prices[i],
                    type='peak',
                    magnitude=magnitude,
                    description=f'Local peak: +{magnitude:.1f}% from recent low'
                ))
        
        # Local trough
        if (prices[i] < prices[i-1] and prices[i] < prices[i-2] and
            prices[i] < prices[i+1] and prices[i] < prices[i+2]):
            
            # Find previous peak
            prev_max = max(prices[max(0, i-20):i])
            magnitude = ((prev_max - prices[i]) / prev_max) * 100 if prev_max > 0 else 0
            
            if magnitude >= threshold_pct:
                inflections.append(InflectionPoint(
                    date=dates[i],
                    price=prices[i],
                    type='trough',
                    magnitude=-magnitude,
                    description=f'Local trough: -{magnitude:.1f}% from recent high'
                ))
    
    # Detect SMA crossovers (20/50)
    for i in range(1, len(prices)):
        if sma_20[i] is None or sma_50[i] is None:
            continue
        if sma_20[i-1] is None or sma_50[i-1] is None:
            continue
        
        # Golden cross (20 crosses above 50)
        if sma_20[i-1] <= sma_50[i-1] and sma_20[i] > sma_50[i]:
            inflections.append(InflectionPoint(
                date=dates[i],
                price=prices[i],
                type='crossover_up',
                magnitude=0,
                description='Golden Cross: 20-day SMA crossed above 50-day SMA (bullish signal)'
            ))
        
        # Death cross (20 crosses below 50)
        if sma_20[i-1] >= sma_50[i-1] and sma_20[i] < sma_50[i]:
            inflections.append(InflectionPoint(
                date=dates[i],
                price=prices[i],
                type='crossover_down',
                magnitude=0,
                description='Death Cross: 20-day SMA crossed below 50-day SMA (bearish signal)'
            ))
    
    return sorted(inflections, key=lambda x: x.date)


def analyze_target_meeting(
    current_price: float,
    price_history: List[float],
    sma_20: List[Optional[float]],
    sma_50: List[Optional[float]],
    price_targets: Dict[str, float],
    earnings_estimates: List[AnalystEstimate]
) -> Dict[str, Any]:
    """
    Analyze whether stock is trending toward meeting analyst targets.
    """
    if len(price_history) < 20:
        return {"status": "insufficient_data"}
    
    # Calculate recent momentum
    recent_prices = price_history[-20:]
    price_change_20d = ((recent_prices[-1] - recent_prices[0]) / recent_prices[0]) * 100
    
    # Calculate trend direction
    if sma_20[-1] and sma_50[-1]:
        trend = "bullish" if sma_20[-1] > sma_50[-1] else "bearish"
        if len(sma_20) >= 5 and sma_20[-5]:
            momentum = "accelerating" if sma_20[-1] > sma_20[-5] else "decelerating"
        else:
            momentum = "stable"
    else:
        trend = "neutral"
        momentum = "stable"
    
    # Price target analysis
    target_analysis = {
        "current_price": float(current_price),
        "trend": trend,
        "momentum": momentum,
        "twenty_day_change_pct": float(price_change_20d),
    }
    
    if price_targets:
        mean_target = price_targets.get("mean", current_price)
        high_target = price_targets.get("high", current_price)
        low_target = price_targets.get("low", current_price)
        
        target_analysis["mean_target"] = float(mean_target)
        target_analysis["upside_to_mean_pct"] = float(((mean_target - current_price) / current_price) * 100) if current_price else 0.0
        target_analysis["upside_to_high_pct"] = float(((high_target - current_price) / current_price) * 100) if current_price else 0.0
        target_analysis["downside_to_low_pct"] = float(((low_target - current_price) / current_price) * 100) if current_price else 0.0
        
        # Will meet target analysis
        if price_change_20d > 0:
            days_to_mean = abs(target_analysis["upside_to_mean_pct"]) / (price_change_20d / 20) if price_change_20d > 0 else None
            target_analysis["estimated_days_to_mean_target"] = int(days_to_mean) if days_to_mean else None
            target_analysis["likely_to_meet_target"] = bool(price_change_20d > 0 and target_analysis["upside_to_mean_pct"] > 0)
        else:
            target_analysis["estimated_days_to_mean_target"] = None
            target_analysis["likely_to_meet_target"] = False
        
        # Confidence level
        if trend == "bullish" and momentum == "accelerating" and target_analysis["upside_to_mean_pct"] > 0:
            target_analysis["confidence"] = "high"
            target_analysis["assessment"] = "Strong bullish momentum suggests target likely to be met or exceeded"
        elif trend == "bullish" and target_analysis["upside_to_mean_pct"] > 0:
            target_analysis["confidence"] = "medium"
            target_analysis["assessment"] = "Positive trend but may face resistance before reaching target"
        elif trend == "bearish" and target_analysis["upside_to_mean_pct"] > 0:
            target_analysis["confidence"] = "low"
            target_analysis["assessment"] = "Current bearish trend makes target achievement unlikely near-term"
        else:
            target_analysis["confidence"] = "medium"
            target_analysis["assessment"] = "Mixed signals; monitor for trend confirmation"
    
    # Earnings estimate analysis
    eps_estimates = [e for e in earnings_estimates if e.estimate_type == 'eps']
    if eps_estimates:
        next_estimate = eps_estimates[0]
        target_analysis["next_earnings_estimate"] = {
            "date": next_estimate.date,
            "mean_eps": next_estimate.mean,
            "low_eps": next_estimate.low,
            "high_eps": next_estimate.high,
            "num_analysts": next_estimate.num_analysts
        }
    
    return target_analysis


# ============================================================================
# API Endpoints
# ============================================================================
@router.get("/analyze/{symbol}", response_model=StockAnalysisResponse)
async def analyze_stock(
    symbol: str,
    period: str = Query("2y", description="Historical period: 1m, 3m, 6m, 1y, 2y, 5y, max"),
    interval: str = Query("1d", description="Data interval: 1d, 1wk, 1mo"),
    inflection_threshold: float = Query(5.0, description="Minimum % change for inflection point detection"),
) -> StockAnalysisResponse:
    """
    Comprehensive stock analysis with historical data, fundamentals, technicals,
    inflection points, and future projections.
    
    Returns:
    - Price history with OHLCV
    - Fundamental metrics over time (P/E, EPS, market cap, employees)
    - Technical indicators (SMAs, EMAs, RSI)
    - Earnings and dividend history
    - Detected inflection points (peaks, troughs, crossovers)
    - Analyst estimates and price targets
    - Target meeting probability analysis
    """
    try:
        import yfinance as yf
        
        ticker = yf.Ticker(symbol.upper())
        
        # Get basic info
        info = ticker.info
        if not info or not info.get("symbol"):
            raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")
        
        # Get historical price data
        hist = ticker.history(period=period, interval=interval)
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No historical data for '{symbol}'")
        
        # Process price history
        price_history = []
        dates = []
        closes = []
        volumes = []
        
        for date, row in hist.iterrows():
            date_str = date.strftime('%Y-%m-%d')
            dates.append(date_str)
            closes.append(row['Close'])
            volumes.append(int(row['Volume']))
            
            price_history.append(PricePoint(
                date=date_str,
                open=round(row['Open'], 2),
                high=round(row['High'], 2),
                low=round(row['Low'], 2),
                close=round(row['Close'], 2),
                volume=int(row['Volume']),
                adjusted_close=round(row['Close'], 2)  # yfinance already adjusts
            ))
        
        # Calculate technical indicators
        sma_20_values = calculate_sma(closes, 20)
        sma_50_values = calculate_sma(closes, 50)
        sma_100_values = calculate_sma(closes, 100)
        sma_200_values = calculate_sma(closes, 200)
        ema_12_values = calculate_ema(closes, 12)
        ema_26_values = calculate_ema(closes, 26)
        rsi_14_values = calculate_rsi(closes, 14)
        volume_sma_20 = calculate_sma([float(v) for v in volumes], 20)
        
        # Create technical indicator time series
        def to_data_points(dates, values):
            return [
                FundamentalDataPoint(date=d, value=round(v, 2))
                for d, v in zip(dates, values) if v is not None
            ]
        
        # Get earnings history
        earnings_history = []
        try:
            earnings_df = ticker.earnings_dates
            if earnings_df is not None and not earnings_df.empty:
                for date, row in earnings_df.iterrows():
                    if date <= datetime.now():  # Only past earnings
                        earnings_history.append(EarningsEvent(
                            date=date.strftime('%Y-%m-%d'),
                            reported_eps=row.get('Reported EPS'),
                            estimated_eps=row.get('EPS Estimate'),
                            surprise_pct=row.get('Surprise(%)'),
                        ))
        except Exception as e:
            logger.debug(f"Could not fetch earnings history: {e}")
        
        # Get dividend history
        dividend_history = []
        try:
            dividends = ticker.dividends
            if dividends is not None and not dividends.empty:
                for date, amount in dividends.items():
                    dividend_history.append(DividendEvent(
                        date=date.strftime('%Y-%m-%d'),
                        amount=round(float(amount), 4)
                    ))
        except Exception as e:
            logger.debug(f"Could not fetch dividend history: {e}")
        
        # Get analyst estimates
        analyst_estimates = []
        try:
            # Future earnings estimates
            earnings_dates = ticker.earnings_dates
            if earnings_dates is not None and not earnings_dates.empty:
                for date, row in earnings_dates.iterrows():
                    if date > datetime.now():  # Future dates
                        eps_est = row.get('EPS Estimate')
                        if eps_est and not np.isnan(eps_est):
                            analyst_estimates.append(AnalystEstimate(
                                date=date.strftime('%Y-%m-%d'),
                                estimate_type='eps',
                                low=eps_est * 0.9,  # Approximate range
                                mean=eps_est,
                                high=eps_est * 1.1,
                                num_analysts=1
                            ))
        except Exception as e:
            logger.debug(f"Could not fetch analyst estimates: {e}")
        
        # Get price targets
        price_targets = {}
        try:
            price_targets = {
                "low": float(info.get("targetLowPrice") or 0),
                "mean": float(info.get("targetMeanPrice") or 0),
                "high": float(info.get("targetHighPrice") or 0),
                "current": float(info.get("currentPrice") or (closes[-1] if closes else 0)),
            }
        except Exception as e:
            logger.debug(f"Could not fetch price targets: {e}")
        
        # Detect inflection points
        inflection_points = detect_inflection_points(
            dates, closes, sma_20_values, sma_50_values, inflection_threshold
        )
        
        # Analyze target meeting probability
        target_analysis = analyze_target_meeting(
            current_price=closes[-1] if closes else 0,
            price_history=closes,
            sma_20=sma_20_values,
            sma_50=sma_50_values,
            price_targets=price_targets,
            earnings_estimates=analyst_estimates
        )
        
        # Create company metrics
        company = CompanyMetrics(
            symbol=info.get("symbol", symbol.upper()),
            name=info.get("longName") or info.get("shortName", ""),
            sector=info.get("sector", ""),
            industry=info.get("industry", ""),
            current_price=info.get("currentPrice") or closes[-1] if closes else 0,
            market_cap=info.get("marketCap", 0),
            pe_ratio=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            peg_ratio=info.get("pegRatio"),
            price_to_book=info.get("priceToBook"),
            price_to_sales=info.get("priceToSalesTrailing12Months"),
            enterprise_value=info.get("enterpriseValue"),
            ev_to_ebitda=info.get("enterpriseToEbitda"),
            profit_margin=info.get("profitMargins"),
            operating_margin=info.get("operatingMargins"),
            roe=info.get("returnOnEquity"),
            roa=info.get("returnOnAssets"),
            debt_to_equity=info.get("debtToEquity"),
            current_ratio=info.get("currentRatio"),
            beta=info.get("beta"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=info.get("fiftyTwoWeekLow"),
            avg_volume=info.get("averageVolume"),
            shares_outstanding=info.get("sharesOutstanding"),
            float_shares=info.get("floatShares"),
            dividend_yield=info.get("dividendYield"),
            payout_ratio=info.get("payoutRatio"),
            employees=info.get("fullTimeEmployees"),
        )
        
        # Get shares outstanding for market cap calculation
        shares_outstanding = info.get("sharesOutstanding", 0)
        
        # Calculate Market Cap history (Price × Shares Outstanding)
        market_cap_history = []
        if shares_outstanding and shares_outstanding > 0:
            for i, (date_str, close_price) in enumerate(zip(dates, closes)):
                market_cap = float(close_price) * shares_outstanding / 1e9  # In billions
                market_cap_history.append(FundamentalDataPoint(
                    date=date_str,
                    value=round(market_cap, 2)
                ))
        
        # Get quarterly EPS from income statement (quarterly_earnings is deprecated)
        eps_history = []
        quarterly_eps_map = {}  # date -> TTM EPS
        try:
            quarterly_income = ticker.quarterly_income_stmt
            if quarterly_income is not None and not quarterly_income.empty:
                # Look for Diluted EPS or Basic EPS
                eps_row_name = None
                for row_name in ['Diluted EPS', 'Basic EPS']:
                    if row_name in quarterly_income.index:
                        eps_row_name = row_name
                        break
                
                if eps_row_name:
                    eps_row = quarterly_income.loc[eps_row_name]
                    quarterly_eps_list = []
                    for date, eps in eps_row.items():
                        if eps is not None and not np.isnan(eps):
                            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
                            quarterly_eps_list.append((date_str, float(eps)))
                            eps_history.append(FundamentalDataPoint(
                                date=date_str,
                                value=round(float(eps), 2)
                            ))
                    
                    # Calculate TTM (Trailing Twelve Month) EPS for each quarter
                    quarterly_eps_list.sort(key=lambda x: x[0])
                    for i in range(3, len(quarterly_eps_list)):
                        # Sum of last 4 quarters
                        ttm_eps = sum([quarterly_eps_list[j][1] for j in range(i-3, i+1)])
                        quarterly_eps_map[quarterly_eps_list[i][0]] = ttm_eps
        except Exception as e:
            logger.debug(f"Could not fetch quarterly earnings: {e}")
        
        # Calculate P/E ratio history
        pe_ratio_history = []
        current_pe = info.get("trailingPE")
        if current_pe and not np.isnan(current_pe):
            # We have current P/E, try to calculate historical P/E
            # Use TTM EPS from quarterly data
            if quarterly_eps_map:
                # For each price point, find the most recent TTM EPS
                sorted_eps_dates = sorted(quarterly_eps_map.keys())
                for date_str, close_price in zip(dates, closes):
                    # Find most recent TTM EPS before this date
                    ttm_eps = None
                    for eps_date in sorted_eps_dates:
                        if eps_date <= date_str:
                            ttm_eps = quarterly_eps_map[eps_date]
                        else:
                            break
                    
                    if ttm_eps and ttm_eps > 0:
                        pe = float(close_price) / ttm_eps
                        if 0 < pe < 500:  # Reasonable P/E range
                            pe_ratio_history.append(FundamentalDataPoint(
                                date=date_str,
                                value=round(pe, 2)
                            ))
        
        # Revenue history
        revenue_history = []
        try:
            # Try quarterly income statement for revenue
            quarterly_income = ticker.quarterly_income_stmt
            if quarterly_income is not None and not quarterly_income.empty:
                if 'Total Revenue' in quarterly_income.index:
                    revenue_row = quarterly_income.loc['Total Revenue']
                    for date, value in revenue_row.items():
                        if value and not np.isnan(value):
                            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
                            revenue_history.append(FundamentalDataPoint(
                                date=date_str,
                                value=round(float(value) / 1e9, 2)  # In billions
                            ))
        except Exception as e:
            logger.debug(f"Could not fetch revenue history: {e}")
        
        # Profit Margin history (Net Income / Revenue)
        profit_margin_history = []
        try:
            quarterly_income = ticker.quarterly_income_stmt
            if quarterly_income is not None and not quarterly_income.empty:
                if 'Total Revenue' in quarterly_income.index and 'Net Income' in quarterly_income.index:
                    revenue_row = quarterly_income.loc['Total Revenue']
                    net_income_row = quarterly_income.loc['Net Income']
                    for date in revenue_row.index:
                        revenue = revenue_row[date]
                        net_income = net_income_row.get(date)
                        if revenue and net_income and not np.isnan(revenue) and not np.isnan(net_income) and revenue > 0:
                            margin = (float(net_income) / float(revenue)) * 100
                            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
                            profit_margin_history.append(FundamentalDataPoint(
                                date=date_str,
                                value=round(margin, 2)
                            ))
        except Exception as e:
            logger.debug(f"Could not fetch profit margin history: {e}")
        
        # Employee count history (limited - yfinance only provides current)
        employee_count_history = []
        if company.employees:
            employee_count_history.append(FundamentalDataPoint(
                date=dates[-1] if dates else datetime.now().strftime('%Y-%m-%d'),
                value=company.employees
            ))
        
        return StockAnalysisResponse(
            symbol=symbol.upper(),
            company=company,
            price_history=price_history,
            pe_ratio_history=pe_ratio_history,
            eps_history=sorted(eps_history, key=lambda x: x.date),
            market_cap_history=market_cap_history,
            revenue_history=sorted(revenue_history, key=lambda x: x.date),
            profit_margin_history=sorted(profit_margin_history, key=lambda x: x.date),
            employee_count_history=employee_count_history,
            sma_20=to_data_points(dates, sma_20_values),
            sma_50=to_data_points(dates, sma_50_values),
            sma_100=to_data_points(dates, sma_100_values),
            sma_200=to_data_points(dates, sma_200_values),
            ema_12=to_data_points(dates, ema_12_values),
            ema_26=to_data_points(dates, ema_26_values),
            rsi_14=to_data_points(dates, rsi_14_values),
            volume_sma_20=to_data_points(dates, volume_sma_20),
            earnings_history=sorted(earnings_history, key=lambda x: x.date, reverse=True)[:20],
            dividend_history=sorted(dividend_history, key=lambda x: x.date, reverse=True)[:40],
            inflection_points=inflection_points,
            analyst_estimates=analyst_estimates[:8],
            price_targets=price_targets,
            target_analysis=target_analysis,
        )
        
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=503, detail="yfinance not installed")
    except Exception as e:
        logger.error(f"Error analyzing stock {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inflection-points/{symbol}")
async def get_inflection_points(
    symbol: str,
    period: str = Query("1y", description="Period: 3m, 6m, 1y, 2y, 5y"),
    threshold: float = Query(5.0, description="Minimum % change for detection"),
) -> dict:
    """
    Get detected inflection points for a stock.
    
    Inflection points include:
    - Local peaks (price reversal from up to down)
    - Local troughs (price reversal from down to up)
    - Golden crosses (bullish SMA crossover)
    - Death crosses (bearish SMA crossover)
    """
    try:
        import yfinance as yf
        
        ticker = yf.Ticker(symbol.upper())
        hist = ticker.history(period=period, interval="1d")
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No data for '{symbol}'")
        
        dates = [d.strftime('%Y-%m-%d') for d in hist.index]
        closes = list(hist['Close'])
        
        sma_20 = calculate_sma(closes, 20)
        sma_50 = calculate_sma(closes, 50)
        
        inflections = detect_inflection_points(dates, closes, sma_20, sma_50, threshold)
        
        return {
            "symbol": symbol.upper(),
            "period": period,
            "threshold_pct": threshold,
            "total_inflection_points": len(inflections),
            "peaks": [i.dict() for i in inflections if i.type == 'peak'],
            "troughs": [i.dict() for i in inflections if i.type == 'trough'],
            "golden_crosses": [i.dict() for i in inflections if i.type == 'crossover_up'],
            "death_crosses": [i.dict() for i in inflections if i.type == 'crossover_down'],
            "all_points": [i.dict() for i in inflections],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting inflection points for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projections/{symbol}")
async def get_projections(
    symbol: str,
) -> dict:
    """
    Get analyst projections and future estimates for a stock.
    
    Includes:
    - Price targets (low, mean, high)
    - Future earnings estimates
    - Revenue projections
    - Probability of meeting targets based on current momentum
    """
    try:
        import yfinance as yf
        
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info
        
        if not info or not info.get("symbol"):
            raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")
        
        # Get current price
        hist = ticker.history(period="1mo", interval="1d")
        current_price = hist['Close'].iloc[-1] if not hist.empty else info.get("currentPrice", 0)
        
        # Price targets
        price_targets = {
            "current": round(current_price, 2),
            "low": info.get("targetLowPrice"),
            "mean": info.get("targetMeanPrice"),
            "high": info.get("targetHighPrice"),
            "median": info.get("targetMedianPrice"),
            "num_analysts": info.get("numberOfAnalystOpinions", 0),
        }
        
        # Calculate upside/downside
        if price_targets["mean"]:
            price_targets["upside_pct"] = round(
                ((price_targets["mean"] - current_price) / current_price) * 100, 2
            )
        
        # Recommendation
        recommendation = {
            "key": info.get("recommendationKey", "none"),
            "mean": info.get("recommendationMean"),  # 1=Strong Buy, 5=Strong Sell
        }
        
        # Future earnings estimates
        earnings_estimates = []
        try:
            earnings_dates = ticker.earnings_dates
            if earnings_dates is not None:
                for date, row in earnings_dates.iterrows():
                    if date > datetime.now():
                        eps_est = row.get('EPS Estimate')
                        if eps_est and not np.isnan(eps_est):
                            earnings_estimates.append({
                                "date": date.strftime('%Y-%m-%d'),
                                "eps_estimate": round(eps_est, 2),
                            })
        except:
            pass
        
        # Growth estimates
        growth = {
            "earnings_growth": info.get("earningsGrowth"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_quarterly_growth": info.get("earningsQuarterlyGrowth"),
        }
        
        return {
            "symbol": symbol.upper(),
            "price_targets": price_targets,
            "recommendation": recommendation,
            "earnings_estimates": earnings_estimates[:4],
            "growth_estimates": growth,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting projections for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare")
async def compare_stocks(
    symbols: str = Query(..., description="Comma-separated symbols to compare"),
) -> dict:
    """
    Compare multiple stocks on key metrics.
    """
    try:
        import yfinance as yf
        
        symbol_list = [s.strip().upper() for s in symbols.split(",")][:10]  # Max 10
        
        comparisons = []
        for symbol in symbol_list:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if info and info.get("symbol"):
                    comparisons.append({
                        "symbol": symbol,
                        "name": info.get("longName") or info.get("shortName", ""),
                        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                        "market_cap": info.get("marketCap"),
                        "pe_ratio": info.get("trailingPE"),
                        "forward_pe": info.get("forwardPE"),
                        "peg_ratio": info.get("pegRatio"),
                        "dividend_yield": info.get("dividendYield"),
                        "beta": info.get("beta"),
                        "profit_margin": info.get("profitMargins"),
                        "roe": info.get("returnOnEquity"),
                        "debt_to_equity": info.get("debtToEquity"),
                        "price_target_mean": info.get("targetMeanPrice"),
                        "recommendation": info.get("recommendationKey"),
                    })
            except Exception as e:
                logger.debug(f"Could not fetch data for {symbol}: {e}")
                comparisons.append({"symbol": symbol, "error": str(e)})
        
        return {
            "symbols": symbol_list,
            "comparison": comparisons,
        }
        
    except Exception as e:
        logger.error(f"Error comparing stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

