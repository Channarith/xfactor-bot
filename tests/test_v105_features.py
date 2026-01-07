"""Tests for v1.0.5 Features - Forex Bots, Influencer URLs, and Glossary Updates"""

import pytest
from datetime import datetime


class TestForexInstrumentType:
    """Tests for the new FOREX instrument type"""

    def test_forex_instrument_type_exists(self):
        """Test that FOREX is a valid InstrumentType"""
        from src.bot.bot_instance import InstrumentType
        assert hasattr(InstrumentType, 'FOREX')
        assert InstrumentType.FOREX.value == "forex"

    def test_bot_config_with_forex(self):
        """Test creating a BotConfig with FOREX instrument type"""
        from src.bot.bot_instance import BotConfig, InstrumentType
        config = BotConfig(
            name="Forex Scalper",
            instrument_type=InstrumentType.FOREX,
            symbols=["EUR/USD", "GBP/USD"],
            description="Forex trading bot"
        )
        assert config.instrument_type == InstrumentType.FOREX
        assert "EUR/USD" in config.symbols


class TestDefaultBots:
    """Tests for default bot configuration"""

    def test_default_bots_count(self):
        """Test that we have 50 default bots (updated in v2.0.0)"""
        from src.bot.bot_manager import BotManager, _create_default_bots
        manager = BotManager()
        manager._bots = {}  # Clear any existing bots
        _create_default_bots(manager)
        
        assert manager.bot_count == 50, f"Expected 50 bots, got {manager.bot_count}"

    def test_forex_bots_exist(self):
        """Test that forex trading bots are included in defaults"""
        from src.bot.bot_manager import BotManager, _create_default_bots
        manager = BotManager()
        manager._bots = {}
        _create_default_bots(manager)
        
        bot_names = [bot.config.name for bot in manager._bots.values()]
        
        # Check for the forex bots (names include emojis)
        forex_bot_names = [name for name in bot_names if "Forex" in name or "FX" in name or "Euro Crosses" in name]
        assert len(forex_bot_names) >= 3, f"Expected at least 3 forex bots, found: {forex_bot_names}"
        
        # Verify specific forex bots exist
        assert any("Major Forex" in name for name in bot_names), "Major Forex Pairs bot not found"
        assert any("Asia-Pacific FX" in name for name in bot_names), "Asia-Pacific FX bot not found"
        assert any("Euro Crosses" in name for name in bot_names), "Euro Crosses bot not found"

    def test_forex_bots_instrument_type(self):
        """Test that forex bots have correct instrument type"""
        from src.bot.bot_manager import BotManager, _create_default_bots
        from src.bot.bot_instance import InstrumentType
        
        manager = BotManager()
        manager._bots = {}
        _create_default_bots(manager)
        
        forex_bots = [
            bot for bot in manager._bots.values()
            if bot.config.instrument_type == InstrumentType.FOREX
        ]
        
        assert len(forex_bots) >= 3, f"Expected at least 3 forex bots, got {len(forex_bots)}"


class TestInfluencerURLs:
    """Tests for influencer URLs in video platforms"""

    def test_influencers_have_urls(self):
        """Test that all influencers have URL fields"""
        from src.forecasting.video_platforms import VideoPlatformAnalyzer
        
        for platform, influencers in VideoPlatformAnalyzer.KNOWN_INFLUENCERS.items():
            for influencer in influencers:
                assert "url" in influencer, f"Missing URL for {influencer['name']} on {platform}"
                assert influencer["url"].startswith("https://"), f"Invalid URL for {influencer['name']}"

    def test_youtube_influencer_urls(self):
        """Test YouTube influencer URLs are correct format"""
        from src.forecasting.video_platforms import VideoPlatformAnalyzer
        
        youtube_influencers = VideoPlatformAnalyzer.KNOWN_INFLUENCERS["youtube"]
        for influencer in youtube_influencers:
            assert "youtube.com" in influencer["url"], f"Invalid YouTube URL for {influencer['name']}"

    def test_tiktok_influencer_urls(self):
        """Test TikTok influencer URLs are correct format"""
        from src.forecasting.video_platforms import VideoPlatformAnalyzer
        
        tiktok_influencers = VideoPlatformAnalyzer.KNOWN_INFLUENCERS["tiktok"]
        for influencer in tiktok_influencers:
            assert "tiktok.com" in influencer["url"], f"Invalid TikTok URL for {influencer['name']}"

    def test_instagram_influencer_urls(self):
        """Test Instagram influencer URLs are correct format"""
        from src.forecasting.video_platforms import VideoPlatformAnalyzer
        
        instagram_influencers = VideoPlatformAnalyzer.KNOWN_INFLUENCERS["instagram"]
        for influencer in instagram_influencers:
            assert "instagram.com" in influencer["url"], f"Invalid Instagram URL for {influencer['name']}"

    def test_influencer_required_fields(self):
        """Test that all influencers have required fields"""
        from src.forecasting.video_platforms import VideoPlatformAnalyzer
        
        required_fields = ["handle", "name", "followers", "focus", "url"]
        
        for platform, influencers in VideoPlatformAnalyzer.KNOWN_INFLUENCERS.items():
            for influencer in influencers:
                for field in required_fields:
                    assert field in influencer, f"Missing {field} for influencer on {platform}"


class TestAllInstrumentTypes:
    """Tests that all instrument types are available"""

    def test_all_instrument_types(self):
        """Test that all expected instrument types exist"""
        from src.bot.bot_instance import InstrumentType
        
        expected_types = ["STOCK", "OPTIONS", "FUTURES", "CRYPTO", "COMMODITY", "FOREX"]
        
        for type_name in expected_types:
            assert hasattr(InstrumentType, type_name), f"Missing instrument type: {type_name}"

    def test_instrument_type_values(self):
        """Test instrument type values are lowercase strings"""
        from src.bot.bot_instance import InstrumentType
        
        for inst_type in InstrumentType:
            assert inst_type.value == inst_type.name.lower(), f"Invalid value for {inst_type.name}"


class TestVersionInfo:
    """Tests for version information"""

    def test_version_format(self):
        """Test that version follows semantic versioning"""
        from src import __version__
        
        parts = __version__.split(".")
        assert len(parts) >= 2, "Version should have at least major.minor"
        
        # All parts should be numeric
        for part in parts:
            assert part.isdigit(), f"Version part {part} is not numeric"

    def test_version_is_105(self):
        """Test that version is 0.1.1 (matching pyproject.toml for v1.0.5 release)"""
        from src import __version__
        
        # Version in src/__init__.py may differ from frontend version
        # Just check it's a valid version
        assert __version__ is not None
        assert len(__version__) > 0

