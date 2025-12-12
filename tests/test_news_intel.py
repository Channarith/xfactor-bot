"""Tests for News Intelligence module."""

import pytest
import tempfile
import os
from unittest.mock import MagicMock, AsyncMock, patch


class TestLocalFileWatcher:
    """Tests for LocalFileWatcher."""

    @pytest.fixture
    def watcher(self):
        from src.news_intel.local_file_watcher import LocalFileWatcher
        return LocalFileWatcher()

    def test_initialization(self, watcher):
        assert watcher.watch_directory is not None
        assert watcher.supported_extensions is not None

    def test_supported_extensions(self, watcher):
        exts = watcher.supported_extensions
        assert '.csv' in exts
        assert '.txt' in exts
        assert '.pdf' in exts

    def test_parse_csv(self, watcher):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("symbol,headline,sentiment\n")
            f.write("AAPL,Apple announces new iPhone,0.8\n")
            f.flush()
            try:
                articles = watcher._parse_csv(f.name)
                assert isinstance(articles, list)
            finally:
                os.unlink(f.name)

    def test_parse_txt(self, watcher):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Breaking News: TSLA hits new high\n")
            f.flush()
            try:
                articles = watcher._parse_txt(f.name)
                assert isinstance(articles, list)
            finally:
                os.unlink(f.name)


class TestSentimentAnalyzer:
    """Tests for sentiment analysis."""

    @pytest.fixture
    def analyzer(self):
        from src.news_intel.sentiment import SentimentAnalyzer
        return SentimentAnalyzer()

    @pytest.mark.asyncio
    async def test_analyze_positive_text(self, analyzer):
        text = "Fantastic earnings beat, stock surges to new highs"
        result = await analyzer.analyze(text)
        assert result is not None
        assert 'sentiment' in result or 'score' in result

    @pytest.mark.asyncio
    async def test_analyze_negative_text(self, analyzer):
        text = "Company misses earnings, stock crashes"
        result = await analyzer.analyze(text)
        assert result is not None


class TestEntityExtractor:
    """Tests for entity extraction."""

    @pytest.fixture
    def extractor(self):
        from src.news_intel.entity_extraction import EntityExtractor
        return EntityExtractor()

    @pytest.mark.asyncio
    async def test_extract_tickers(self, extractor):
        text = "AAPL and NVDA are leading the tech rally"
        entities = await extractor.extract(text)
        assert isinstance(entities, dict)

