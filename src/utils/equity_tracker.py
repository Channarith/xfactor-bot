"""
Equity tracking and persistence for portfolio performance history.

Tracks portfolio equity over time and persists to disk for historical charting.
"""

import json
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from loguru import logger


class EquityTracker:
    """Tracks and persists portfolio equity over time."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize equity tracker.
        
        Args:
            data_dir: Directory to store equity data (defaults to ~/.xfactor-bot/data)
        """
        if data_dir is None:
            data_dir = Path.home() / ".xfactor-bot" / "data"
        
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.equity_file = self.data_dir / "equity_history.json"
        self.history: Dict[str, float] = {}
        self.last_save_time: Optional[datetime] = None
        
        # Load existing history
        self._load_history()
    
    def _load_history(self) -> None:
        """Load equity history from disk."""
        try:
            if self.equity_file.exists():
                with open(self.equity_file, 'r') as f:
                    data = json.load(f)
                    self.history = data.get('history', {})
                    logger.info(f"Loaded {len(self.history)} equity history entries")
            else:
                logger.info("No existing equity history found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load equity history: {e}")
            self.history = {}
    
    def record_equity(self, equity: float, timestamp: Optional[datetime] = None) -> None:
        """
        Record current equity value.
        
        Args:
            equity: Current portfolio equity value
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Store at daily resolution (one entry per day)
        date_key = timestamp.date().isoformat()
        
        # Only update if equity is different or it's a new day
        if date_key not in self.history or abs(self.history[date_key] - equity) > 0.01:
            self.history[date_key] = round(equity, 2)
            logger.debug(f"Recorded equity: ${equity:,.2f} for {date_key}")
            
            # Auto-save periodically
            self._auto_save()
    
    def _auto_save(self) -> None:
        """Auto-save if enough time has passed."""
        now = datetime.now()
        if self.last_save_time is None or (now - self.last_save_time).total_seconds() > 60:
            self.save()
    
    def save(self) -> bool:
        """
        Save equity history to disk.
        
        Returns:
            True if saved successfully
        """
        try:
            data = {
                'last_updated': datetime.now().isoformat(),
                'total_entries': len(self.history),
                'history': self.history,
            }
            
            with open(self.equity_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.last_save_time = datetime.now()
            logger.debug(f"Saved {len(self.history)} equity history entries")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save equity history: {e}")
            return False
    
    def get_history(
        self, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, any]]:
        """
        Get equity history for a date range.
        
        Args:
            start_date: Start date (defaults to 90 days ago)
            end_date: End date (defaults to today)
            
        Returns:
            List of {date, value} dicts sorted by date
        """
        if end_date is None:
            end_date = date.today()
        
        if start_date is None:
            start_date = end_date - timedelta(days=90)
        
        # Filter and convert to list
        filtered = []
        for date_key, value in self.history.items():
            entry_date = date.fromisoformat(date_key)
            if start_date <= entry_date <= end_date:
                filtered.append({
                    'date': date_key,
                    'value': value,
                })
        
        # Sort by date
        filtered.sort(key=lambda x: x['date'])
        
        return filtered
    
    def get_current_equity(self) -> Optional[float]:
        """Get the most recent equity value."""
        if not self.history:
            return None
        
        # Get the latest date
        latest_date = max(self.history.keys())
        return self.history[latest_date]
    
    def get_return_pct(self, days: int = 30) -> Optional[float]:
        """
        Calculate percentage return over a period.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Percentage return or None if insufficient data
        """
        today = date.today()
        start_date = today - timedelta(days=days)
        
        # Get values
        current = self.get_current_equity()
        
        # Find closest historical value
        start_value = None
        for i in range(days + 7):  # Look back a bit further if needed
            check_date = (start_date - timedelta(days=i)).isoformat()
            if check_date in self.history:
                start_value = self.history[check_date]
                break
        
        if current is None or start_value is None or start_value == 0:
            return None
        
        return ((current - start_value) / start_value) * 100
    
    def cleanup_old_data(self, keep_days: int = 365) -> int:
        """
        Remove equity data older than specified days.
        
        Args:
            keep_days: Number of days to keep
            
        Returns:
            Number of entries removed
        """
        cutoff_date = date.today() - timedelta(days=keep_days)
        
        old_keys = [
            k for k in self.history.keys()
            if date.fromisoformat(k) < cutoff_date
        ]
        
        for key in old_keys:
            del self.history[key]
        
        if old_keys:
            logger.info(f"Cleaned up {len(old_keys)} old equity entries")
            self.save()
        
        return len(old_keys)


# Global instance
_equity_tracker: Optional[EquityTracker] = None


def get_equity_tracker() -> EquityTracker:
    """Get or create global equity tracker instance."""
    global _equity_tracker
    if _equity_tracker is None:
        _equity_tracker = EquityTracker()
    return _equity_tracker
