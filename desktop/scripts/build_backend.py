#!/usr/bin/env python3
"""
Build the XFactor Bot backend as a standalone executable
Uses PyInstaller to create a single binary that can be bundled with Tauri
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DESKTOP_DIR = SCRIPT_DIR.parent
TAURI_DIR = DESKTOP_DIR / "src-tauri"
BINARIES_DIR = TAURI_DIR / "binaries"

def get_target_triple():
    """Get the Rust target triple for the current platform"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "darwin":
        if machine == "arm64":
            return "aarch64-apple-darwin"
        else:
            return "x86_64-apple-darwin"
    elif system == "windows":
        return "x86_64-pc-windows-msvc"
    elif system == "linux":
        if machine == "aarch64":
            return "aarch64-unknown-linux-gnu"
        else:
            return "x86_64-unknown-linux-gnu"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Build XFactor Bot Backend')
    parser.add_argument('--target', type=str, help='Target triple (e.g., aarch64-apple-darwin, x86_64-apple-darwin)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Building XFactor Bot Backend")
    print("=" * 60)
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"[OK] PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Create binaries directory
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get target triple (use argument if provided, otherwise auto-detect)
    target_triple = args.target if args.target else get_target_triple()
    print(f"[OK] Target: {target_triple}")
    
    # Check if cross-compiling (PyInstaller can only build for current platform)
    current_triple = get_target_triple()
    if target_triple != current_triple:
        print(f"[WARN] Cross-compilation requested ({target_triple}) but running on {current_triple}")
        print(f"       PyInstaller can only build for the current platform.")
        print(f"       Creating a placeholder for {target_triple}...")
        
        # Create a placeholder script that will be replaced with actual binary
        placeholder_path = BINARIES_DIR / f"xfactor-backend-{target_triple}"
        with open(placeholder_path, 'w') as f:
            f.write("#!/bin/sh\\necho 'This is a placeholder. Build on the target platform.'\\n")
        if platform.system() != "Windows":
            os.chmod(placeholder_path, 0o755)
        print(f"       Created placeholder: {placeholder_path}")
        return
    
    # Output binary name (Tauri expects name-target format)
    if platform.system() == "Windows":
        binary_name = f"xfactor-backend-{target_triple}.exe"
    else:
        binary_name = f"xfactor-backend-{target_triple}"
    
    output_path = BINARIES_DIR / binary_name
    
    # Build with PyInstaller
    print(f"\nBuilding backend executable...")
    print(f"Output: {output_path}")
    
    # Change to project root for imports to work
    os.chdir(PROJECT_ROOT)
    
    # CRITICAL: Add project root to PYTHONPATH so PyInstaller can find src package
    current_pythonpath = os.environ.get('PYTHONPATH', '')
    os.environ['PYTHONPATH'] = str(PROJECT_ROOT) + os.pathsep + current_pythonpath
    print(f"[INFO] Set PYTHONPATH to include: {PROJECT_ROOT}")
    
    # Also add to sys.path for the current process
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    
    # Verify src package is importable
    try:
        import src
        import src.bot.agentic_tuner
        print(f"[OK] src package is importable from: {src.__file__}")
        print(f"[OK] src.bot.agentic_tuner is importable")
    except ImportError as e:
        print(f"[ERROR] Cannot import src package: {e}")
        print(f"[ERROR] This will cause PyInstaller to fail!")
        print(f"[INFO] Current sys.path: {sys.path[:5]}")
    
    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", f"xfactor-backend-{target_triple}",
        "--distpath", str(BINARIES_DIR),
        "--workpath", str(DESKTOP_DIR / "build"),
        "--specpath", str(DESKTOP_DIR / "build"),
        # =====================================================================
        # CRITICAL: Multiple approaches to ensure src package is bundled
        # =====================================================================
        "--paths", str(PROJECT_ROOT),
        "--paths", ".",
        # Collect ALL submodules of the src package
        "--collect-submodules", "src",
        "--collect-data", "src",
        # =====================================================================
        # CRITICAL: Include ALL src.* modules as hidden imports
        # PyInstaller doesn't auto-discover these from dynamic imports
        # =====================================================================
        # src.utils
        "--hidden-import", "src",
        "--hidden-import", "src.utils",
        "--hidden-import", "src.utils.helpers",
        "--hidden-import", "src.utils.logger",
        # src.accounts
        "--hidden-import", "src.accounts",
        "--hidden-import", "src.accounts.account_manager",
        # src.ai
        "--hidden-import", "src.ai",
        "--hidden-import", "src.ai.assistant",
        "--hidden-import", "src.ai.context_builder",
        "--hidden-import", "src.ai.ollama_client",
        # src.api
        "--hidden-import", "src.api",
        "--hidden-import", "src.api.auth",
        "--hidden-import", "src.api.main",
        "--hidden-import", "src.api.routes",
        "--hidden-import", "src.api.routes.admin",
        "--hidden-import", "src.api.routes.agentic_tuning",
        "--hidden-import", "src.api.routes.ai",
        "--hidden-import", "src.api.routes.bot_risk",
        "--hidden-import", "src.api.routes.bots",
        "--hidden-import", "src.api.routes.commodities",
        "--hidden-import", "src.api.routes.compliance",
        "--hidden-import", "src.api.routes.config",
        "--hidden-import", "src.api.routes.crypto",
        "--hidden-import", "src.api.routes.fees",
        "--hidden-import", "src.api.routes.forecasting",
        "--hidden-import", "src.api.routes.forex",
        "--hidden-import", "src.api.routes.integrations",
        "--hidden-import", "src.api.routes.manual_trading",
        "--hidden-import", "src.api.routes.market",
        "--hidden-import", "src.api.routes.momentum",
        "--hidden-import", "src.api.routes.news",
        "--hidden-import", "src.api.routes.optimizer",
        "--hidden-import", "src.api.routes.orders",
        "--hidden-import", "src.api.routes.performance",
        "--hidden-import", "src.api.routes.positions",
        "--hidden-import", "src.api.routes.risk",
        "--hidden-import", "src.api.routes.screener",
        "--hidden-import", "src.api.routes.seasonal",
        "--hidden-import", "src.api.routes.stock_analysis",
        "--hidden-import", "src.api.routes.strategies",
        "--hidden-import", "src.api.routes.symbols",
        "--hidden-import", "src.api.routes.tradingview",
        "--hidden-import", "src.api.routes.video_sentiment",
        # src.backtesting
        "--hidden-import", "src.backtesting",
        "--hidden-import", "src.backtesting.backtest_engine",
        # src.banking
        "--hidden-import", "src.banking",
        "--hidden-import", "src.banking.plaid_client",
        # src.bot - ALL submodules (agentic_tuner was missing!)
        "--hidden-import", "src.bot",
        "--hidden-import", "src.bot.agentic_tuner",
        "--hidden-import", "src.bot.auto_optimizer",
        "--hidden-import", "src.bot.bot_instance",
        "--hidden-import", "src.bot.bot_manager",
        "--hidden-import", "src.bot.momentum_bots",
        "--hidden-import", "src.bot.risk_manager",
        # src.brokers
        "--hidden-import", "src.brokers",
        "--hidden-import", "src.brokers.base",
        "--hidden-import", "src.brokers.registry",
        "--hidden-import", "src.brokers.alpaca_broker",
        "--hidden-import", "src.brokers.ibkr_broker",
        "--hidden-import", "src.brokers.ninjatrader",
        "--hidden-import", "src.brokers.saved_connections",
        "--hidden-import", "src.brokers.schwab_broker",
        "--hidden-import", "src.brokers.tradier_broker",
        # src.circuit_breakers
        "--hidden-import", "src.circuit_breakers",
        "--hidden-import", "src.circuit_breakers.kill_switch",
        # src.compliance
        "--hidden-import", "src.compliance",
        "--hidden-import", "src.compliance.compliance_manager",
        # src.config
        "--hidden-import", "src.config",
        "--hidden-import", "src.config.exchanges",
        "--hidden-import", "src.config.instruments",
        "--hidden-import", "src.config.limits",
        "--hidden-import", "src.config.settings",
        # src.connectors
        "--hidden-import", "src.connectors",
        "--hidden-import", "src.connectors.ibkr_connector",
        # src.data
        "--hidden-import", "src.data",
        "--hidden-import", "src.data.growth_screener",
        "--hidden-import", "src.data.market_data_providers",
        "--hidden-import", "src.data.market_data",
        "--hidden-import", "src.data.momentum_screener",
        "--hidden-import", "src.data.news_momentum",
        "--hidden-import", "src.data.redis_cache",
        "--hidden-import", "src.data.sectors",
        "--hidden-import", "src.data.symbol_universe",
        "--hidden-import", "src.data.timescale_client",
        "--hidden-import", "src.data.universe_scanner",
        # src.data_sources
        "--hidden-import", "src.data_sources",
        "--hidden-import", "src.data_sources.ainvest",
        "--hidden-import", "src.data_sources.base",
        "--hidden-import", "src.data_sources.commodities",
        "--hidden-import", "src.data_sources.crypto",
        "--hidden-import", "src.data_sources.registry",
        "--hidden-import", "src.data_sources.tradingview",
        # src.execution
        "--hidden-import", "src.execution",
        "--hidden-import", "src.execution.order_manager",
        "--hidden-import", "src.execution.position_tracker",
        # src.fees
        "--hidden-import", "src.fees",
        "--hidden-import", "src.fees.fee_tracker",
        # src.forecasting
        "--hidden-import", "src.forecasting",
        "--hidden-import", "src.forecasting.buzz_detector",
        "--hidden-import", "src.forecasting.catalyst_tracker",
        "--hidden-import", "src.forecasting.hypothesis_generator",
        "--hidden-import", "src.forecasting.social_sentiment",
        "--hidden-import", "src.forecasting.speculation_scorer",
        "--hidden-import", "src.forecasting.video_platforms",
        # src.forex
        "--hidden-import", "src.forex",
        "--hidden-import", "src.forex.brokers",
        "--hidden-import", "src.forex.brokers.metatrader",
        "--hidden-import", "src.forex.brokers.oanda",
        "--hidden-import", "src.forex.core",
        "--hidden-import", "src.forex.currency_strength",
        "--hidden-import", "src.forex.economic_calendar",
        "--hidden-import", "src.forex.strategies",
        # src.mcp
        "--hidden-import", "src.mcp",
        "--hidden-import", "src.mcp.server",
        # src.ml
        "--hidden-import", "src.ml",
        "--hidden-import", "src.ml.strategy_optimizer",
        # src.monitoring
        "--hidden-import", "src.monitoring",
        "--hidden-import", "src.monitoring.metrics",
        # src.news_intel
        "--hidden-import", "src.news_intel",
        "--hidden-import", "src.news_intel.entity_extractor",
        "--hidden-import", "src.news_intel.local_file_watcher",
        "--hidden-import", "src.news_intel.news_aggregator",
        "--hidden-import", "src.news_intel.sentiment_engine",
        # src.portfolio
        "--hidden-import", "src.portfolio",
        "--hidden-import", "src.portfolio.rebalancer",
        "--hidden-import", "src.portfolio.tax_harvester",
        # src.risk
        "--hidden-import", "src.risk",
        "--hidden-import", "src.risk.portfolio_optimizer",
        "--hidden-import", "src.risk.position_sizer",
        "--hidden-import", "src.risk.risk_manager",
        # src.service
        "--hidden-import", "src.service",
        "--hidden-import", "src.service.bot_service",
        "--hidden-import", "src.service.scheduler",
        # src.social
        "--hidden-import", "src.social",
        "--hidden-import", "src.social.trading",
        # src.strategies
        "--hidden-import", "src.strategies",
        "--hidden-import", "src.strategies.base_strategy",
        "--hidden-import", "src.strategies.market_regime",
        "--hidden-import", "src.strategies.martingale",
        "--hidden-import", "src.strategies.mean_reversion",
        "--hidden-import", "src.strategies.momentum",
        "--hidden-import", "src.strategies.news_sentiment",
        "--hidden-import", "src.strategies.seasonal_events",
        "--hidden-import", "src.strategies.ta_compat",
        "--hidden-import", "src.strategies.technical",
        "--hidden-import", "src.strategies.templates",
        "--hidden-import", "src.strategies.visual_builder",
        "--hidden-import", "src.strategies.volatility_adaptive",
        # =====================================================================
        # Collect all submodules for all key packages
        # Web framework
        "--collect-all", "uvicorn",
        "--collect-all", "fastapi",
        "--collect-all", "starlette",
        "--collect-all", "pydantic",
        "--collect-all", "pydantic_settings",
        "--collect-all", "python_multipart",
        # HTTP/WebSocket clients
        "--collect-all", "httpx",
        "--collect-all", "httpcore",
        "--collect-all", "h11",
        "--collect-all", "websockets",
        "--collect-all", "websocket",
        "--collect-all", "aiohttp",
        "--collect-all", "aiosignal",
        "--collect-all", "aiohappyeyeballs",
        "--collect-all", "requests",
        "--collect-all", "urllib3",
        # Data processing
        "--collect-all", "pandas",
        # pandas_ta removed - using ta_compat wrapper instead
        "--collect-all", "ta",
        "--collect-all", "numpy",
        "--collect-all", "polars",
        # Trading
        "--collect-all", "ib_insync",
        # Database
        "--collect-all", "sqlalchemy",
        "--collect-all", "asyncpg",
        "--collect-all", "redis",
        # Async
        "--collect-all", "anyio",
        "--collect-all", "sniffio",
        "--collect-all", "nest_asyncio",
        # Scheduling
        "--collect-all", "apscheduler",
        # Scraping/Parsing
        "--collect-all", "beautifulsoup4",
        "--collect-all", "bs4",
        "--collect-all", "feedparser",
        "--collect-all", "lxml",
        # Typing
        "--collect-all", "typing_extensions",
        "--hidden-import", "typing_extensions",
        # Other utilities
        "--collect-all", "orjson",
        "--collect-all", "python_dotenv",
        "--collect-all", "loguru",
        "--collect-all", "pytz",
        "--collect-all", "dateutil",
        "--collect-all", "certifi",
        "--collect-all", "yaml",
        "--collect-all", "jinja2",
        "--collect-all", "click",
        "--collect-all", "tqdm",
        "--collect-all", "regex",
        "--collect-all", "tokenizers",
        "--collect-all", "safetensors",
        "--collect-all", "huggingface_hub",
        "--collect-all", "numba",
        "--collect-all", "langdetect",
        "--collect-all", "deep_translator",
        "--collect-all", "openpyxl",
        "--collect-all", "praw",
        "--collect-all", "prawcore",
        "--collect-all", "psycopg2",
        "--collect-all", "watchfiles",
        "--collect-all", "httptools",
        "--collect-all", "attrs",
        "--collect-all", "multidict",
        "--collect-all", "frozenlist",
        "--collect-all", "yarl",
        "--collect-all", "idna",
        "--collect-all", "charset_normalizer",
        "--collect-all", "tenacity",
        # AI/ML API clients (configurable via admin panel)
        "--collect-all", "openai",
        "--collect-all", "anthropic",
        # Exclude local ML frameworks (use API-based LLMs instead)
        "--exclude-module", "torch",
        "--exclude-module", "transformers",
        "--exclude-module", "tensorflow",
        "--exclude-module", "keras",
        # Exclude unused packages
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "PIL",
        "--exclude-module", "cv2",
        "--exclude-module", "tensorflow",
        "--exclude-module", "keras",
        "--exclude-module", "jax",
        "--exclude-module", "flax",
        "--exclude-module", "optax",
        "--exclude-module", "IPython",
        "--exclude-module", "jupyter",
        "--exclude-module", "notebook",
        "--exclude-module", "playwright",
        # Clean build
        "--clean",
        "--noconfirm",
        # Entry point
        str(SCRIPT_DIR / "run_backend.py"),
    ]
    
    # Platform-specific exclusions
    if platform.system() == "Windows":
        # uvloop is Unix-only
        cmd.extend(["--exclude-module", "uvloop"])
        # psycopg2-binary has issues on Windows, use psycopg2 or skip
        cmd.extend(["--exclude-module", "psycopg2"])
        print("[INFO] Windows build - excluding uvloop, psycopg2")
    else:
        # Include uvloop on Unix for better performance
        cmd.extend(["--collect-all", "uvloop"])
        cmd.insert(3, "--windowed")  # No console on macOS/Linux
    
    # Linux-specific
    if platform.system() == "Linux":
        # Exclude X11/GUI packages not needed for server
        cmd.extend(["--exclude-module", "PyQt5"])
        cmd.extend(["--exclude-module", "PyQt6"])
        cmd.extend(["--exclude-module", "PySide6"])
        print("[INFO] Linux build - excluding GUI packages")
    
    print(f"\nRunning: {' '.join(cmd[:10])}...")
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"\n[ERROR] Build failed with exit code {result.returncode}")
        sys.exit(1)
    
    # Verify output
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n[OK] Backend built successfully!")
        print(f"     Path: {output_path}")
        print(f"     Size: {size_mb:.1f} MB")
        
        # Make executable on Unix
        if platform.system() != "Windows":
            os.chmod(output_path, 0o755)
            print(f"     Permissions: executable")
    else:
        print(f"\n[ERROR] Output file not found: {output_path}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Backend build complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()

