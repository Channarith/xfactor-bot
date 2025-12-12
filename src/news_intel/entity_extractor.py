"""
Entity Extractor for identifying companies and tickers in news text.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger


@dataclass
class ExtractedEntities:
    """Extracted entities from text."""
    primary_tickers: list[str] = field(default_factory=list)
    secondary_tickers: list[str] = field(default_factory=list)
    companies: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    people: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    
    @property
    def all_tickers(self) -> list[str]:
        return self.primary_tickers + self.secondary_tickers
    
    @property
    def has_tickers(self) -> bool:
        return len(self.primary_tickers) > 0


class EntityExtractor:
    """
    Extract entities from news text and map to tickers.
    """
    
    def __init__(self):
        """Initialize entity extractor."""
        # Company to ticker mapping
        self._company_to_ticker = {
            # Tech Giants
            "apple": "AAPL",
            "microsoft": "MSFT",
            "google": "GOOGL",
            "alphabet": "GOOGL",
            "amazon": "AMZN",
            "meta": "META",
            "facebook": "META",
            "nvidia": "NVDA",
            "tesla": "TSLA",
            "netflix": "NFLX",
            "adobe": "ADBE",
            "salesforce": "CRM",
            "oracle": "ORCL",
            "intel": "INTC",
            "amd": "AMD",
            "broadcom": "AVGO",
            "qualcomm": "QCOM",
            "cisco": "CSCO",
            "ibm": "IBM",
            
            # Finance
            "jpmorgan": "JPM",
            "jp morgan": "JPM",
            "goldman sachs": "GS",
            "goldman": "GS",
            "morgan stanley": "MS",
            "bank of america": "BAC",
            "wells fargo": "WFC",
            "citigroup": "C",
            "citi": "C",
            "blackrock": "BLK",
            "visa": "V",
            "mastercard": "MA",
            "american express": "AXP",
            "amex": "AXP",
            
            # Healthcare
            "johnson & johnson": "JNJ",
            "j&j": "JNJ",
            "pfizer": "PFE",
            "moderna": "MRNA",
            "unitedhealth": "UNH",
            "eli lilly": "LLY",
            "lilly": "LLY",
            "abbvie": "ABBV",
            "merck": "MRK",
            "novartis": "NVS",
            
            # Consumer
            "walmart": "WMT",
            "costco": "COST",
            "home depot": "HD",
            "nike": "NKE",
            "starbucks": "SBUX",
            "mcdonald's": "MCD",
            "mcdonalds": "MCD",
            "coca-cola": "KO",
            "pepsi": "PEP",
            "pepsico": "PEP",
            "procter & gamble": "PG",
            "p&g": "PG",
            
            # International/ADRs
            "alibaba": "BABA",
            "tencent": "TCEHY",
            "tsmc": "TSM",
            "taiwan semiconductor": "TSM",
            "samsung": "SSNLF",
            "toyota": "TM",
            "sony": "SONY",
            "novo nordisk": "NVO",
            "asml": "ASML",
            "sap": "SAP",
            "jd.com": "JD",
            "jd": "JD",
            "baidu": "BIDU",
            "pinduoduo": "PDD",
            "pdd": "PDD",
            
            # Energy
            "exxon": "XOM",
            "exxonmobil": "XOM",
            "chevron": "CVX",
            "shell": "SHEL",
            "bp": "BP",
            "conocophillips": "COP",
            
            # Other
            "disney": "DIS",
            "boeing": "BA",
            "3m": "MMM",
            "caterpillar": "CAT",
            "ge": "GE",
            "general electric": "GE",
            "lockheed": "LMT",
            "lockheed martin": "LMT",
            "raytheon": "RTX",
        }
        
        # Sector keywords
        self._sector_keywords = {
            "technology": ["tech", "software", "ai", "artificial intelligence", "cloud", "semiconductor", "chip"],
            "healthcare": ["pharma", "biotech", "drug", "fda", "medical", "hospital", "healthcare"],
            "finance": ["bank", "financial", "insurance", "investment", "fed", "interest rate"],
            "energy": ["oil", "gas", "energy", "solar", "renewable", "opec"],
            "consumer": ["retail", "consumer", "e-commerce", "shopping"],
            "industrial": ["manufacturing", "industrial", "aerospace", "defense"],
            "real estate": ["real estate", "reit", "property", "housing"],
        }
        
        # Related tickers (competitors, suppliers, etc.)
        self._related_tickers = {
            "NVDA": ["AMD", "INTC", "TSM", "AVGO", "QCOM"],
            "AAPL": ["MSFT", "GOOGL", "SSNLF"],
            "TSLA": ["F", "GM", "RIVN", "LCID", "NIO"],
            "AMZN": ["WMT", "TGT", "COST", "SHOP"],
            "META": ["GOOGL", "SNAP", "PINS", "TWTR"],
            "GOOGL": ["META", "MSFT", "AMZN"],
            "MSFT": ["GOOGL", "AMZN", "CRM", "ORCL"],
        }
        
        # ETF mappings for sectors
        self._sector_etfs = {
            "technology": ["XLK", "QQQ", "SMH", "SOXX"],
            "healthcare": ["XLV", "IBB", "XBI"],
            "finance": ["XLF", "KBE", "KRE"],
            "energy": ["XLE", "OIH", "XOP"],
            "consumer": ["XLY", "XLP", "XRT"],
            "industrial": ["XLI", "ITA"],
            "real estate": ["XLRE", "VNQ"],
        }
    
    def extract(self, text: str) -> ExtractedEntities:
        """
        Extract entities from text.
        
        Args:
            text: News text to analyze
            
        Returns:
            ExtractedEntities object
        """
        text_lower = text.lower()
        
        entities = ExtractedEntities()
        
        # Extract tickers mentioned directly (e.g., $NVDA, NVDA)
        ticker_pattern = r'\$?([A-Z]{1,5})(?:\s|$|[,.])'
        direct_tickers = re.findall(ticker_pattern, text)
        
        # Filter to known tickers
        known_tickers = set(self._company_to_ticker.values())
        for ticker in direct_tickers:
            if ticker in known_tickers and ticker not in entities.primary_tickers:
                entities.primary_tickers.append(ticker)
        
        # Extract companies by name
        for company, ticker in self._company_to_ticker.items():
            if company in text_lower and ticker not in entities.primary_tickers:
                entities.primary_tickers.append(ticker)
                entities.companies.append(company.title())
        
        # Extract sectors
        for sector, keywords in self._sector_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if sector not in entities.sectors:
                        entities.sectors.append(sector)
                    break
        
        # Add related tickers as secondary
        for primary in entities.primary_tickers:
            related = self._related_tickers.get(primary, [])
            for ticker in related:
                if ticker not in entities.primary_tickers and ticker not in entities.secondary_tickers:
                    entities.secondary_tickers.append(ticker)
        
        # Add sector ETFs as secondary
        for sector in entities.sectors:
            etfs = self._sector_etfs.get(sector, [])
            for etf in etfs:
                if etf not in entities.secondary_tickers:
                    entities.secondary_tickers.append(etf)
        
        return entities
    
    def get_ticker_for_company(self, company: str) -> Optional[str]:
        """Get ticker for a company name."""
        return self._company_to_ticker.get(company.lower())
    
    def get_related_tickers(self, ticker: str) -> list[str]:
        """Get related tickers for a ticker."""
        return self._related_tickers.get(ticker, [])
    
    def get_sector_etfs(self, sector: str) -> list[str]:
        """Get ETFs for a sector."""
        return self._sector_etfs.get(sector.lower(), [])

