# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for XFactor Bot Backend
Creates a standalone executable that runs the FastAPI server
"""

import sys
from pathlib import Path

# Project root
project_root = Path(__file__).parent.parent.parent

block_cipher = None

a = Analysis(
    [str(project_root / 'desktop' / 'scripts' / 'run_backend.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Include frontend dist for serving static files
        (str(project_root / 'frontend' / 'dist'), 'frontend/dist'),
    ],
    hiddenimports=[
        # Uvicorn
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        # Core dependencies
        'fastapi',
        'starlette',
        'pydantic',
        'pydantic_settings',
        'httpx',
        'websockets',
        'aiohttp',
        'sqlalchemy',
        'pandas',
        'numpy',
        'yfinance',
        # src package - ALL modules explicitly listed
        'src',
        # src.utils
        'src.utils',
        'src.utils.helpers',
        'src.utils.logger',
        # src.accounts
        'src.accounts',
        'src.accounts.account_manager',
        # src.ai
        'src.ai',
        'src.ai.assistant',
        'src.ai.context_builder',
        'src.ai.ollama_client',
        # src.api
        'src.api',
        'src.api.auth',
        'src.api.main',
        'src.api.routes',
        'src.api.routes.admin',
        'src.api.routes.agentic_tuning',
        'src.api.routes.ai',
        'src.api.routes.bot_risk',
        'src.api.routes.bots',
        'src.api.routes.commodities',
        'src.api.routes.compliance',
        'src.api.routes.config',
        'src.api.routes.crypto',
        'src.api.routes.fees',
        'src.api.routes.forecasting',
        'src.api.routes.forex',
        'src.api.routes.integrations',
        'src.api.routes.manual_trading',
        'src.api.routes.market',
        'src.api.routes.momentum',
        'src.api.routes.news',
        'src.api.routes.optimizer',
        'src.api.routes.orders',
        'src.api.routes.performance',
        'src.api.routes.positions',
        'src.api.routes.risk',
        'src.api.routes.screener',
        'src.api.routes.seasonal',
        'src.api.routes.stock_analysis',
        'src.api.routes.strategies',
        'src.api.routes.symbols',
        'src.api.routes.tradingview',
        'src.api.routes.video_sentiment',
        # src.backtesting
        'src.backtesting',
        'src.backtesting.backtest_engine',
        # src.banking
        'src.banking',
        'src.banking.plaid_client',
        # src.bot - ALL submodules explicitly
        'src.bot',
        'src.bot.agentic_tuner',
        'src.bot.auto_optimizer',
        'src.bot.bot_instance',
        'src.bot.bot_manager',
        'src.bot.momentum_bots',
        'src.bot.risk_manager',
        # src.brokers - ALL brokers
        'src.brokers',
        'src.brokers.base',
        'src.brokers.registry',
        'src.brokers.alpaca_broker',
        'src.brokers.ibkr_broker',
        'src.brokers.ninjatrader',
        'src.brokers.saved_connections',
        'src.brokers.schwab_broker',
        'src.brokers.tradier_broker',
        # src.circuit_breakers
        'src.circuit_breakers',
        'src.circuit_breakers.kill_switch',
        # src.compliance
        'src.compliance',
        'src.compliance.compliance_manager',
        # src.config
        'src.config',
        'src.config.exchanges',
        'src.config.instruments',
        'src.config.limits',
        'src.config.settings',
        # src.connectors
        'src.connectors',
        'src.connectors.ibkr_connector',
        # src.data
        'src.data',
        'src.data.growth_screener',
        'src.data.market_data_providers',
        'src.data.market_data',
        'src.data.momentum_screener',
        'src.data.news_momentum',
        'src.data.redis_cache',
        'src.data.sectors',
        'src.data.symbol_universe',
        'src.data.timescale_client',
        'src.data.universe_scanner',
        # src.data_sources
        'src.data_sources',
        'src.data_sources.ainvest',
        'src.data_sources.base',
        'src.data_sources.commodities',
        'src.data_sources.crypto',
        'src.data_sources.registry',
        'src.data_sources.tradingview',
        # src.execution
        'src.execution',
        'src.execution.order_manager',
        'src.execution.position_tracker',
        # src.fees
        'src.fees',
        'src.fees.fee_tracker',
        # src.forecasting
        'src.forecasting',
        'src.forecasting.buzz_detector',
        'src.forecasting.catalyst_tracker',
        'src.forecasting.hypothesis_generator',
        'src.forecasting.social_sentiment',
        'src.forecasting.speculation_scorer',
        'src.forecasting.video_platforms',
        # src.forex
        'src.forex',
        'src.forex.brokers',
        'src.forex.brokers.metatrader',
        'src.forex.brokers.oanda',
        'src.forex.core',
        'src.forex.currency_strength',
        'src.forex.economic_calendar',
        'src.forex.strategies',
        # src.mcp
        'src.mcp',
        'src.mcp.server',
        # src.ml
        'src.ml',
        'src.ml.strategy_optimizer',
        # src.monitoring
        'src.monitoring',
        'src.monitoring.metrics',
        # src.news_intel
        'src.news_intel',
        'src.news_intel.entity_extractor',
        'src.news_intel.local_file_watcher',
        'src.news_intel.news_aggregator',
        'src.news_intel.sentiment_engine',
        # src.portfolio
        'src.portfolio',
        'src.portfolio.rebalancer',
        'src.portfolio.tax_harvester',
        # src.risk
        'src.risk',
        'src.risk.portfolio_optimizer',
        'src.risk.position_sizer',
        'src.risk.risk_manager',
        # src.service
        'src.service',
        'src.service.bot_service',
        'src.service.scheduler',
        # src.social
        'src.social',
        'src.social.trading',
        # src.strategies - ALL strategies
        'src.strategies',
        'src.strategies.base_strategy',
        'src.strategies.market_regime',
        'src.strategies.martingale',
        'src.strategies.mean_reversion',
        'src.strategies.momentum',
        'src.strategies.news_sentiment',
        'src.strategies.seasonal_events',
        'src.strategies.ta_compat',
        'src.strategies.technical',
        'src.strategies.templates',
        'src.strategies.visual_builder',
        'src.strategies.volatility_adaptive',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'cv2',
        'torch',
        'tensorflow',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='xfactor-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# For macOS, create an app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='xfactor-backend.app',
        icon=None,
        bundle_identifier='com.xfactor.backend',
        info_plist={
            'LSBackgroundOnly': True,  # Run as background process
        },
    )

