"""News intelligence module for sentiment analysis and signal generation."""

from src.news_intel.news_aggregator import NewsAggregator
from src.news_intel.sentiment_engine import SentimentEngine
from src.news_intel.entity_extractor import EntityExtractor
from src.news_intel.local_file_watcher import LocalFileWatcher

__all__ = [
    "NewsAggregator",
    "SentimentEngine",
    "EntityExtractor",
    "LocalFileWatcher",
]

