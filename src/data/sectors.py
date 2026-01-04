"""
Sector Definitions - 25+ sectors and sub-sectors with symbol classifications.

Standard S&P 500 Sectors (11):
- Technology, Healthcare, Financials, Energy, Consumer Discretionary
- Consumer Staples, Industrials, Materials, Utilities, Real Estate, Communication

Extended Sub-Sectors (14+):
- Semiconductors, AI/ML, Electric Vehicles, Cannabis, Uranium/Nuclear
- Cybersecurity, Biotechnology, Aerospace/Defense, Clean Energy
- Gaming/Esports, Cloud/SaaS, Fintech, Rare Earth Metals, Space
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from enum import Enum


class SectorCategory(str, Enum):
    """Sector category types."""
    STANDARD = "standard"     # S&P 500 standard sectors
    EXTENDED = "extended"     # Sub-sectors and themes
    COMMODITY = "commodity"   # Commodity-focused
    CRYPTO = "crypto"        # Cryptocurrency-related


@dataclass
class SectorDefinition:
    """Definition of a sector or sub-sector."""
    id: str
    name: str
    category: SectorCategory
    etf: str                          # Primary sector ETF
    etf_leveraged: Optional[str] = None  # Leveraged ETF if available
    description: str = ""
    keywords: List[str] = None        # Keywords for classification
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


# ============================================================================
# STANDARD S&P 500 SECTORS (11)
# ============================================================================

STANDARD_SECTORS: Dict[str, SectorDefinition] = {
    "technology": SectorDefinition(
        id="technology",
        name="Technology",
        category=SectorCategory.STANDARD,
        etf="XLK",
        etf_leveraged="TECL",
        description="Information technology companies including software, hardware, and IT services",
        keywords=["software", "hardware", "computer", "technology", "IT", "tech"],
    ),
    "healthcare": SectorDefinition(
        id="healthcare",
        name="Healthcare",
        category=SectorCategory.STANDARD,
        etf="XLV",
        description="Healthcare providers, pharmaceuticals, biotechnology, and medical devices",
        keywords=["healthcare", "medical", "pharmaceutical", "drug", "hospital"],
    ),
    "financials": SectorDefinition(
        id="financials",
        name="Financials",
        category=SectorCategory.STANDARD,
        etf="XLF",
        etf_leveraged="FAS",
        description="Banks, insurance companies, and diversified financial services",
        keywords=["bank", "insurance", "financial", "asset management", "investment"],
    ),
    "energy": SectorDefinition(
        id="energy",
        name="Energy",
        category=SectorCategory.STANDARD,
        etf="XLE",
        etf_leveraged="ERX",
        description="Oil, gas, and energy equipment and services",
        keywords=["oil", "gas", "petroleum", "energy", "drilling", "refining"],
    ),
    "consumer_discretionary": SectorDefinition(
        id="consumer_discretionary",
        name="Consumer Discretionary",
        category=SectorCategory.STANDARD,
        etf="XLY",
        description="Retail, automotive, leisure, and consumer services",
        keywords=["retail", "automotive", "consumer", "leisure", "hospitality"],
    ),
    "consumer_staples": SectorDefinition(
        id="consumer_staples",
        name="Consumer Staples",
        category=SectorCategory.STANDARD,
        etf="XLP",
        description="Food, beverages, household products, and tobacco",
        keywords=["food", "beverage", "household", "grocery", "tobacco"],
    ),
    "industrials": SectorDefinition(
        id="industrials",
        name="Industrials",
        category=SectorCategory.STANDARD,
        etf="XLI",
        description="Aerospace, defense, machinery, and transportation",
        keywords=["industrial", "machinery", "transportation", "manufacturing"],
    ),
    "materials": SectorDefinition(
        id="materials",
        name="Materials",
        category=SectorCategory.STANDARD,
        etf="XLB",
        description="Chemicals, construction materials, metals, and mining",
        keywords=["chemical", "mining", "metals", "materials", "construction"],
    ),
    "utilities": SectorDefinition(
        id="utilities",
        name="Utilities",
        category=SectorCategory.STANDARD,
        etf="XLU",
        description="Electric, gas, and water utilities",
        keywords=["utility", "electric", "gas", "water", "power"],
    ),
    "real_estate": SectorDefinition(
        id="real_estate",
        name="Real Estate",
        category=SectorCategory.STANDARD,
        etf="XLRE",
        description="Real estate investment trusts (REITs) and real estate services",
        keywords=["real estate", "REIT", "property", "housing"],
    ),
    "communication": SectorDefinition(
        id="communication",
        name="Communication Services",
        category=SectorCategory.STANDARD,
        etf="XLC",
        description="Telecommunications, media, and entertainment",
        keywords=["telecom", "media", "entertainment", "communication", "streaming"],
    ),
}


# ============================================================================
# EXTENDED SUB-SECTORS (14+)
# ============================================================================

EXTENDED_SECTORS: Dict[str, SectorDefinition] = {
    "semiconductors": SectorDefinition(
        id="semiconductors",
        name="Semiconductors",
        category=SectorCategory.EXTENDED,
        etf="SMH",
        etf_leveraged="SOXL",
        description="Semiconductor design, manufacturing, and equipment",
        keywords=["semiconductor", "chip", "processor", "memory", "fab"],
    ),
    "ai_ml": SectorDefinition(
        id="ai_ml",
        name="AI & Machine Learning",
        category=SectorCategory.EXTENDED,
        etf="BOTZ",
        description="Artificial intelligence, machine learning, and robotics",
        keywords=["artificial intelligence", "AI", "machine learning", "robotics", "automation"],
    ),
    "ev_electric": SectorDefinition(
        id="ev_electric",
        name="Electric Vehicles",
        category=SectorCategory.EXTENDED,
        etf="DRIV",
        etf_leveraged="TSLL",
        description="Electric vehicles, batteries, and charging infrastructure",
        keywords=["electric vehicle", "EV", "battery", "charging", "autonomous"],
    ),
    "cannabis": SectorDefinition(
        id="cannabis",
        name="Cannabis",
        category=SectorCategory.EXTENDED,
        etf="MSOS",
        description="Cannabis producers, retailers, and related services",
        keywords=["cannabis", "marijuana", "hemp", "CBD"],
    ),
    "uranium_nuclear": SectorDefinition(
        id="uranium_nuclear",
        name="Uranium & Nuclear",
        category=SectorCategory.EXTENDED,
        etf="URA",
        description="Uranium mining and nuclear energy",
        keywords=["uranium", "nuclear", "atomic", "enrichment"],
    ),
    "cybersecurity": SectorDefinition(
        id="cybersecurity",
        name="Cybersecurity",
        category=SectorCategory.EXTENDED,
        etf="HACK",
        etf_leveraged="UCYB",
        description="Cybersecurity software and services",
        keywords=["cybersecurity", "security", "firewall", "encryption", "threat"],
    ),
    "biotech": SectorDefinition(
        id="biotech",
        name="Biotechnology",
        category=SectorCategory.EXTENDED,
        etf="XBI",
        etf_leveraged="LABU",
        description="Biotechnology research and development",
        keywords=["biotech", "biotechnology", "gene", "therapy", "clinical"],
    ),
    "aerospace_defense": SectorDefinition(
        id="aerospace_defense",
        name="Aerospace & Defense",
        category=SectorCategory.EXTENDED,
        etf="ITA",
        description="Aerospace manufacturing and defense contractors",
        keywords=["aerospace", "defense", "military", "aircraft", "missile"],
    ),
    "clean_energy": SectorDefinition(
        id="clean_energy",
        name="Clean Energy",
        category=SectorCategory.EXTENDED,
        etf="ICLN",
        etf_leveraged="ACES",
        description="Solar, wind, and renewable energy",
        keywords=["solar", "wind", "renewable", "clean energy", "green"],
    ),
    "gaming_esports": SectorDefinition(
        id="gaming_esports",
        name="Gaming & Esports",
        category=SectorCategory.EXTENDED,
        etf="ESPO",
        description="Video games, esports, and gaming hardware",
        keywords=["gaming", "video game", "esports", "console"],
    ),
    "cloud_saas": SectorDefinition(
        id="cloud_saas",
        name="Cloud & SaaS",
        category=SectorCategory.EXTENDED,
        etf="WCLD",
        description="Cloud computing and software-as-a-service",
        keywords=["cloud", "SaaS", "software as a service", "infrastructure"],
    ),
    "fintech": SectorDefinition(
        id="fintech",
        name="Fintech",
        category=SectorCategory.EXTENDED,
        etf="FINX",
        description="Financial technology and payments",
        keywords=["fintech", "payment", "digital banking", "blockchain"],
    ),
    "rare_earth": SectorDefinition(
        id="rare_earth",
        name="Rare Earth Metals",
        category=SectorCategory.EXTENDED,
        etf="REMX",
        description="Rare earth elements and strategic metals mining",
        keywords=["rare earth", "lithium", "cobalt", "strategic metals"],
    ),
    "space": SectorDefinition(
        id="space",
        name="Space & Satellite",
        category=SectorCategory.EXTENDED,
        etf="UFO",
        description="Space exploration, satellites, and related technology",
        keywords=["space", "satellite", "rocket", "orbit", "aerospace"],
    ),
}


# ============================================================================
# COMMODITY SECTORS
# ============================================================================

COMMODITY_SECTORS: Dict[str, SectorDefinition] = {
    "gold": SectorDefinition(
        id="gold",
        name="Gold",
        category=SectorCategory.COMMODITY,
        etf="GLD",
        etf_leveraged="NUGT",
        description="Gold mining and bullion",
        keywords=["gold", "mining", "precious metal"],
    ),
    "silver": SectorDefinition(
        id="silver",
        name="Silver",
        category=SectorCategory.COMMODITY,
        etf="SLV",
        description="Silver mining and bullion",
        keywords=["silver", "mining", "precious metal"],
    ),
    "oil_gas": SectorDefinition(
        id="oil_gas",
        name="Oil & Gas",
        category=SectorCategory.COMMODITY,
        etf="USO",
        etf_leveraged="UCO",
        description="Oil and natural gas",
        keywords=["oil", "gas", "crude", "natural gas", "petroleum"],
    ),
    "agriculture": SectorDefinition(
        id="agriculture",
        name="Agriculture",
        category=SectorCategory.COMMODITY,
        etf="DBA",
        description="Agricultural commodities and farming",
        keywords=["agriculture", "farming", "grain", "corn", "wheat", "soybean"],
    ),
    "lithium_battery": SectorDefinition(
        id="lithium_battery",
        name="Lithium & Batteries",
        category=SectorCategory.COMMODITY,
        etf="LIT",
        description="Lithium mining and battery technology",
        keywords=["lithium", "battery", "energy storage"],
    ),
    "copper": SectorDefinition(
        id="copper",
        name="Copper & Base Metals",
        category=SectorCategory.COMMODITY,
        etf="CPER",
        description="Copper and industrial metals",
        keywords=["copper", "aluminum", "zinc", "nickel", "base metal"],
    ),
}


# ============================================================================
# CRYPTO-RELATED SECTORS
# ============================================================================

CRYPTO_SECTORS: Dict[str, SectorDefinition] = {
    "crypto_etfs": SectorDefinition(
        id="crypto_etfs",
        name="Crypto ETFs",
        category=SectorCategory.CRYPTO,
        etf="IBIT",
        description="Cryptocurrency ETFs and trusts",
        keywords=["bitcoin", "ethereum", "crypto", "cryptocurrency"],
    ),
    "crypto_miners": SectorDefinition(
        id="crypto_miners",
        name="Crypto Mining",
        category=SectorCategory.CRYPTO,
        etf="WGMI",
        description="Cryptocurrency mining companies",
        keywords=["mining", "bitcoin mining", "crypto mining", "ASIC"],
    ),
    "blockchain": SectorDefinition(
        id="blockchain",
        name="Blockchain & Web3",
        category=SectorCategory.CRYPTO,
        etf="BLOK",
        description="Blockchain technology and Web3 companies",
        keywords=["blockchain", "web3", "decentralized", "smart contract"],
    ),
}


# ============================================================================
# SECTOR SYMBOL MAPPINGS
# ============================================================================

# Pre-defined symbols for each sector (top holdings + key players)
SECTOR_SYMBOLS: Dict[str, List[str]] = {
    # Standard sectors
    "technology": ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "ADBE", "ACN", "AMD", "CSCO", "INTC", "IBM", "NOW", "INTU", "QCOM"],
    "healthcare": ["UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY", "AMGN", "CVS", "MDT", "ISRG", "GILD"],
    "financials": ["BRK.B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "SPGI", "BLK", "AXP", "C", "SCHW", "PNC", "USB"],
    "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "WMB", "KMI", "HAL", "DVN", "HES", "BKR"],
    "consumer_discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "TJX", "BKNG", "CMG", "ORLY", "MAR", "DHI", "GM", "F"],
    "consumer_staples": ["PG", "KO", "PEP", "COST", "WMT", "PM", "MO", "MDLZ", "CL", "KMB", "GIS", "STZ", "KHC", "HSY", "KR"],
    "industrials": ["CAT", "RTX", "UNP", "HON", "DE", "BA", "UPS", "GE", "LMT", "ADP", "FDX", "ETN", "ITW", "NSC", "WM"],
    "materials": ["LIN", "APD", "SHW", "ECL", "FCX", "NUE", "NEM", "CTVA", "DOW", "DD", "VMC", "MLM", "ALB", "PPG", "CF"],
    "utilities": ["NEE", "SO", "DUK", "CEG", "SRE", "AEP", "D", "EXC", "XEL", "PEG", "WEC", "ED", "AWK", "ES", "DTE"],
    "real_estate": ["PLD", "AMT", "EQIX", "CCI", "PSA", "SPG", "O", "WELL", "DLR", "AVB", "VICI", "EQR", "VTR", "SBAC", "ARE"],
    "communication": ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "VZ", "T", "TMUS", "CHTR", "WBD", "OMC", "EA", "TTWO", "MTCH", "LYV"],
    
    # Extended sectors
    "semiconductors": ["NVDA", "AMD", "INTC", "AVGO", "QCOM", "TXN", "MU", "ADI", "LRCX", "KLAC", "AMAT", "MRVL", "NXPI", "ON", "MCHP"],
    "ai_ml": ["NVDA", "MSFT", "GOOGL", "AMZN", "META", "PLTR", "AI", "PATH", "SNOW", "DDOG", "MDB", "CRWD", "SPLK", "PANW", "ZS"],
    "ev_electric": ["TSLA", "RIVN", "LCID", "NIO", "XPEV", "LI", "F", "GM", "CHPT", "BLNK", "EVGO", "QS", "GOEV", "FSR", "WKHS"],
    "cannabis": ["TLRY", "CGC", "ACB", "CRON", "SNDL", "OGI", "HEXO", "VFF", "GRWG", "CURLF", "GTBIF", "TCNNF", "CRLBF", "TRSSF"],
    "uranium_nuclear": ["CCJ", "UEC", "DNN", "NNE", "UUUU", "URG", "LEU", "BWXT", "OKLO", "SMR", "LTBR", "EU", "GEV", "PALAF"],
    "cybersecurity": ["CRWD", "PANW", "ZS", "FTNT", "OKTA", "NET", "S", "CYBR", "QLYS", "TENB", "RPD", "VRNS", "SAIL", "RDWR"],
    "biotech": ["MRNA", "REGN", "VRTX", "GILD", "BIIB", "ILMN", "SGEN", "ALNY", "BMRN", "EXAS", "IONS", "SRPT", "INCY", "NBIX", "PCVX"],
    "aerospace_defense": ["LMT", "RTX", "BA", "NOC", "GD", "TDG", "LHX", "HII", "LDOS", "BWXT", "HEI", "TXT", "SPR", "CW", "MOG.A"],
    "clean_energy": ["ENPH", "SEDG", "FSLR", "RUN", "CSIQ", "JKS", "NOVA", "ARRY", "MAXN", "SPWR", "BE", "PLUG", "BLDP", "FCEL", "CLNE"],
    "gaming_esports": ["NVDA", "AMD", "EA", "TTWO", "ATVI", "RBLX", "U", "PLTK", "GMBL", "EGLX", "SLGG", "SKLZ"],
    "cloud_saas": ["CRM", "NOW", "WDAY", "SNOW", "DDOG", "ZM", "DOCU", "TWLO", "OKTA", "CRWD", "NET", "MDB", "ESTC", "CFLT", "GTLB"],
    "fintech": ["SQ", "PYPL", "COIN", "AFRM", "UPST", "SOFI", "NU", "HOOD", "BILL", "TOST", "PAYO", "FOUR", "RELY", "LPRO", "OPEN"],
    "rare_earth": ["MP", "LAC", "ALB", "LTHM", "SQM", "PLL", "LIVENT", "ALTM", "SGML", "UAMY", "LIT", "REMX"],
    "space": ["RKLB", "ASTR", "SPCE", "ASTS", "BKSY", "RDW", "LUNR", "SATL", "IRDM", "VSAT", "GSAT", "MAXR"],
    
    # Commodity sectors
    "gold": ["NEM", "GOLD", "AEM", "FNV", "WPM", "KGC", "AU", "PAAS", "HL", "CDE", "EGO", "AG", "IAG", "BTG"],
    "silver": ["SLV", "AG", "PAAS", "HL", "CDE", "EXK", "FSM", "MAG", "SVM", "SILV"],
    "oil_gas": ["XOM", "CVX", "COP", "SLB", "EOG", "OXY", "MPC", "VLO", "PSX", "HES", "DVN", "HAL", "BKR", "FANG", "PXD"],
    "agriculture": ["ADM", "BG", "DE", "AGCO", "CF", "MOS", "NTR", "FMC", "CTVA", "INGR", "SMG"],
    "lithium_battery": ["ALB", "SQM", "LAC", "LTHM", "PLL", "LIVENT", "SGML", "PANW", "QS", "MVST", "DCRC"],
    "copper": ["FCX", "SCCO", "TECK", "AA", "NUE", "STLD", "X", "CLF", "CMC", "RS", "ATI"],
    
    # Crypto sectors
    "crypto_etfs": ["IBIT", "FBTC", "GBTC", "ETHE", "BITO", "BTF", "ARKB", "HODL"],
    "crypto_miners": ["MARA", "RIOT", "CLSK", "BITF", "HUT", "CIFR", "IREN", "BTBT", "BTDR", "WULF"],
    "blockchain": ["COIN", "MSTR", "SQ", "PYPL", "HOOD", "SI", "GLXY", "NVDA", "AMD"],
}


# ============================================================================
# ALL SECTORS COMBINED
# ============================================================================

ALL_SECTORS: Dict[str, SectorDefinition] = {
    **STANDARD_SECTORS,
    **EXTENDED_SECTORS,
    **COMMODITY_SECTORS,
    **CRYPTO_SECTORS,
}

# Alias for backwards compatibility
SECTORS = ALL_SECTORS


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_sector(sector_id: str) -> Optional[SectorDefinition]:
    """Get a sector definition by ID."""
    return ALL_SECTORS.get(sector_id)


def get_sector_symbols(sector_id: str) -> List[str]:
    """Get symbols for a sector."""
    return SECTOR_SYMBOLS.get(sector_id, [])


def get_sector_etf(sector_id: str) -> Optional[str]:
    """Get the primary ETF for a sector."""
    sector = ALL_SECTORS.get(sector_id)
    return sector.etf if sector else None


def get_all_sector_ids() -> List[str]:
    """Get all sector IDs."""
    return list(ALL_SECTORS.keys())


def get_sectors_by_category(category: SectorCategory) -> Dict[str, SectorDefinition]:
    """Get all sectors in a category."""
    return {k: v for k, v in ALL_SECTORS.items() if v.category == category}


def get_standard_sectors() -> Dict[str, SectorDefinition]:
    """Get standard S&P 500 sectors."""
    return STANDARD_SECTORS.copy()


def get_extended_sectors() -> Dict[str, SectorDefinition]:
    """Get extended sub-sectors."""
    return EXTENDED_SECTORS.copy()


def find_sector_for_symbol(symbol: str) -> Optional[str]:
    """Find which sector a symbol belongs to (first match)."""
    symbol = symbol.upper()
    for sector_id, symbols in SECTOR_SYMBOLS.items():
        if symbol in symbols:
            return sector_id
    return None


def get_all_sector_etfs() -> List[str]:
    """Get all sector ETFs."""
    etfs = []
    for sector in ALL_SECTORS.values():
        etfs.append(sector.etf)
        if sector.etf_leveraged:
            etfs.append(sector.etf_leveraged)
    return list(set(etfs))


def get_sector_summary() -> List[dict]:
    """Get summary of all sectors for API."""
    return [
        {
            "id": sector.id,
            "name": sector.name,
            "category": sector.category.value,
            "etf": sector.etf,
            "etf_leveraged": sector.etf_leveraged,
            "symbol_count": len(SECTOR_SYMBOLS.get(sector.id, [])),
        }
        for sector in ALL_SECTORS.values()
    ]

