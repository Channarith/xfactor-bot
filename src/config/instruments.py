"""
Tradeable instruments configuration.
Defines the universe of instruments the bot can trade.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AssetClass(str, Enum):
    """Asset class types."""
    STOCK = "STK"
    OPTION = "OPT"
    FUTURE = "FUT"
    FOREX = "CASH"
    INDEX = "IND"
    ETF = "ETF"
    CRYPTO = "CRYPTO"


class Exchange(str, Enum):
    """Major exchanges."""
    # US Exchanges
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    AMEX = "AMEX"
    ARCA = "ARCA"
    BATS = "BATS"
    IEX = "IEX"
    CBOE = "CBOE"
    CME = "CME"
    
    # International Exchanges
    LSE = "LSE"  # London
    TSE = "TSE"  # Tokyo
    HKEX = "HKEX"  # Hong Kong
    SSE = "SSE"  # Shanghai
    SZSE = "SZSE"  # Shenzhen
    KRX = "KRX"  # Korea
    ASX = "ASX"  # Australia
    TSX = "TSX"  # Toronto
    XETRA = "XETRA"  # Germany
    EURONEXT = "EURONEXT"  # Europe
    
    # Smart routing
    SMART = "SMART"


class Currency(str, Enum):
    """Currencies."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    HKD = "HKD"
    CNY = "CNY"
    CNH = "CNH"
    KRW = "KRW"
    AUD = "AUD"
    CAD = "CAD"
    CHF = "CHF"


@dataclass
class Instrument:
    """Represents a tradeable instrument."""
    symbol: str
    asset_class: AssetClass
    exchange: Exchange
    currency: Currency
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    
    def to_ibkr_contract(self) -> dict:
        """Convert to IBKR contract specification."""
        return {
            "symbol": self.symbol,
            "secType": self.asset_class.value,
            "exchange": self.exchange.value,
            "currency": self.currency.value,
        }


# Major US ETFs
MAJOR_ETFS = [
    Instrument("SPY", AssetClass.ETF, Exchange.SMART, Currency.USD, "S&P 500 ETF"),
    Instrument("QQQ", AssetClass.ETF, Exchange.SMART, Currency.USD, "Nasdaq 100 ETF"),
    Instrument("IWM", AssetClass.ETF, Exchange.SMART, Currency.USD, "Russell 2000 ETF"),
    Instrument("DIA", AssetClass.ETF, Exchange.SMART, Currency.USD, "Dow Jones ETF"),
    Instrument("VTI", AssetClass.ETF, Exchange.SMART, Currency.USD, "Total Stock Market ETF"),
    Instrument("VOO", AssetClass.ETF, Exchange.SMART, Currency.USD, "Vanguard S&P 500"),
    Instrument("VXX", AssetClass.ETF, Exchange.SMART, Currency.USD, "VIX Short-Term Futures"),
    Instrument("GLD", AssetClass.ETF, Exchange.SMART, Currency.USD, "Gold ETF"),
    Instrument("SLV", AssetClass.ETF, Exchange.SMART, Currency.USD, "Silver ETF"),
    Instrument("TLT", AssetClass.ETF, Exchange.SMART, Currency.USD, "20+ Year Treasury ETF"),
    Instrument("XLF", AssetClass.ETF, Exchange.SMART, Currency.USD, "Financial Select Sector"),
    Instrument("XLK", AssetClass.ETF, Exchange.SMART, Currency.USD, "Technology Select Sector"),
    Instrument("XLE", AssetClass.ETF, Exchange.SMART, Currency.USD, "Energy Select Sector"),
    Instrument("XLV", AssetClass.ETF, Exchange.SMART, Currency.USD, "Health Care Select Sector"),
    Instrument("SMH", AssetClass.ETF, Exchange.SMART, Currency.USD, "Semiconductor ETF"),
    Instrument("SOXX", AssetClass.ETF, Exchange.SMART, Currency.USD, "iShares Semiconductor"),
]

# Major US Tech Stocks
MAJOR_TECH_STOCKS = [
    Instrument("AAPL", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Apple Inc", "Technology"),
    Instrument("MSFT", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Microsoft Corp", "Technology"),
    Instrument("GOOGL", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Alphabet Inc", "Technology"),
    Instrument("AMZN", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Amazon.com Inc", "Technology"),
    Instrument("META", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Meta Platforms", "Technology"),
    Instrument("NVDA", AssetClass.STOCK, Exchange.SMART, Currency.USD, "NVIDIA Corp", "Technology"),
    Instrument("TSLA", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Tesla Inc", "Technology"),
    Instrument("AMD", AssetClass.STOCK, Exchange.SMART, Currency.USD, "AMD Inc", "Technology"),
    Instrument("INTC", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Intel Corp", "Technology"),
    Instrument("CRM", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Salesforce Inc", "Technology"),
    Instrument("ORCL", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Oracle Corp", "Technology"),
    Instrument("ADBE", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Adobe Inc", "Technology"),
    Instrument("NFLX", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Netflix Inc", "Technology"),
    Instrument("AVGO", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Broadcom Inc", "Technology"),
    Instrument("QCOM", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Qualcomm Inc", "Technology"),
]

# International ADRs
INTERNATIONAL_ADRS = [
    Instrument("BABA", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Alibaba Group", "Technology"),
    Instrument("TSM", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Taiwan Semiconductor", "Technology"),
    Instrument("NVO", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Novo Nordisk", "Healthcare"),
    Instrument("ASML", AssetClass.STOCK, Exchange.SMART, Currency.USD, "ASML Holding", "Technology"),
    Instrument("TM", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Toyota Motor", "Automotive"),
    Instrument("SAP", AssetClass.STOCK, Exchange.SMART, Currency.USD, "SAP SE", "Technology"),
    Instrument("SONY", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Sony Group", "Technology"),
    Instrument("PDD", AssetClass.STOCK, Exchange.SMART, Currency.USD, "PDD Holdings", "Retail"),
    Instrument("JD", AssetClass.STOCK, Exchange.SMART, Currency.USD, "JD.com Inc", "Retail"),
    Instrument("BIDU", AssetClass.STOCK, Exchange.SMART, Currency.USD, "Baidu Inc", "Technology"),
]

# All tradeable instruments
ALL_INSTRUMENTS = MAJOR_ETFS + MAJOR_TECH_STOCKS + INTERNATIONAL_ADRS


def get_instrument_by_symbol(symbol: str) -> Optional[Instrument]:
    """Get instrument by symbol."""
    for instrument in ALL_INSTRUMENTS:
        if instrument.symbol.upper() == symbol.upper():
            return instrument
    return None


def get_instruments_by_sector(sector: str) -> list[Instrument]:
    """Get all instruments in a sector."""
    return [i for i in ALL_INSTRUMENTS if i.sector and i.sector.lower() == sector.lower()]

