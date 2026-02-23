"""
Saved Bots Manager.

Stores bot configurations and state persistently for:
- Resume bots on app restart
- Preserve position tracking
- Maintain trade history and statistics

Storage location: ~/.xfactor-bot/saved_bots.json
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

from loguru import logger


@dataclass
class SavedBotState:
    """State information for a saved bot."""
    bot_id: str
    config: Dict[str, Any]  # Full BotConfig as dict
    was_running: bool = False  # Whether bot was running when saved
    auto_start: bool = False  # Whether to auto-start on load
    created_at: str = ""
    last_updated: str = ""
    # Statistics snapshot (optional, for display before full load)
    stats_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class SavedPositionTracking:
    """Saved position tracking entry."""
    symbol: str
    broker: str
    bot_id: str
    bot_name: str
    opened_at: Optional[str] = None
    quantity: float = 0.0
    synced: bool = False
    strategy: Optional[str] = None


class SavedBotsManager:
    """
    Manages saved bot configurations and state.
    
    Stores bot data in a JSON file for persistence across app restarts.
    Position tracking is also saved to restore bot-position associations.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the saved bots manager.
        
        Args:
            config_dir: Directory to store configuration files.
                       Defaults to ~/.xfactor-bot/
        """
        if config_dir:
            self._config_dir = Path(config_dir)
        else:
            # Use home directory for persistent storage
            self._config_dir = Path.home() / ".xfactor-bot"
        
        self._bots_file = self._config_dir / "saved_bots.json"
        self._positions_file = self._config_dir / "position_tracking.json"
        self._saved_bots: Dict[str, SavedBotState] = {}
        self._position_tracking: Dict[str, SavedPositionTracking] = {}
        
        # Initialize
        self._ensure_config_dir()
        
        logger.debug(f"SavedBotsManager initialized with config_dir: {self._config_dir}")
    
    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        
        # Set restrictive permissions on Unix
        try:
            os.chmod(self._config_dir, 0o700)
        except Exception:
            pass
    
    def load_bots(self) -> List[SavedBotState]:
        """
        Load saved bot configurations from disk.
        
        Returns:
            List of SavedBotState objects
        """
        if not self._bots_file.exists():
            logger.debug("No saved bots file found")
            return []
        
        try:
            with open(self._bots_file, 'r') as f:
                data = json.load(f)
            
            self._saved_bots.clear()
            
            for bot_data in data.get('bots', []):
                try:
                    bot_state = SavedBotState(
                        bot_id=bot_data.get('bot_id', ''),
                        config=bot_data.get('config', {}),
                        was_running=bot_data.get('was_running', False),
                        auto_start=bot_data.get('auto_start', False),
                        created_at=bot_data.get('created_at', ''),
                        last_updated=bot_data.get('last_updated', ''),
                        stats_snapshot=bot_data.get('stats_snapshot', {}),
                    )
                    if bot_state.bot_id:
                        self._saved_bots[bot_state.bot_id] = bot_state
                except Exception as e:
                    logger.error(f"Error loading bot state: {e}")
            
            logger.info(f"Loaded {len(self._saved_bots)} saved bot configurations")
            return list(self._saved_bots.values())
            
        except Exception as e:
            logger.error(f"Error loading saved bots: {e}")
            return []
    
    def save_bots(self, bots: List[Dict[str, Any]]) -> bool:
        """
        Save bot configurations to disk.
        
        Args:
            bots: List of bot data dicts with keys:
                  - bot_id: str
                  - config: dict (BotConfig.to_dict())
                  - is_running: bool
                  - auto_start: bool (optional)
                  - stats: dict (optional stats snapshot)
                  
        Returns:
            True if saved successfully
        """
        try:
            now = datetime.now().isoformat()
            
            saved_bots = []
            for bot_data in bots:
                bot_id = bot_data.get('bot_id', '')
                if not bot_id:
                    continue
                    
                # Get existing state for created_at
                existing = self._saved_bots.get(bot_id)
                created_at = existing.created_at if existing else now
                
                saved_bot = {
                    'bot_id': bot_id,
                    'config': bot_data.get('config', {}),
                    'was_running': bot_data.get('is_running', False),
                    'auto_start': bot_data.get('auto_start', bot_data.get('is_running', False)),
                    'created_at': created_at,
                    'last_updated': now,
                    'stats_snapshot': bot_data.get('stats', {}),
                }
                saved_bots.append(saved_bot)
                
                # Update in-memory cache
                self._saved_bots[bot_id] = SavedBotState(**saved_bot)
            
            data = {
                'version': 1,
                'saved_at': now,
                'bots_count': len(saved_bots),
                'bots': saved_bots,
            }
            
            with open(self._bots_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Set restrictive permissions
            try:
                os.chmod(self._bots_file, 0o600)
            except Exception:
                pass
            
            logger.info(f"Saved {len(saved_bots)} bot configurations to {self._bots_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving bots: {e}")
            return False
    
    def save_single_bot(self, bot_id: str, config: Dict[str, Any], 
                        is_running: bool = False, stats: Dict[str, Any] = None) -> bool:
        """
        Save or update a single bot configuration.
        
        Args:
            bot_id: Bot ID
            config: BotConfig as dict
            is_running: Whether bot is currently running
            stats: Optional stats snapshot
            
        Returns:
            True if saved successfully
        """
        try:
            # Load existing bots first
            if not self._saved_bots:
                self.load_bots()
            
            now = datetime.now().isoformat()
            
            # Get existing state
            existing = self._saved_bots.get(bot_id)
            
            self._saved_bots[bot_id] = SavedBotState(
                bot_id=bot_id,
                config=config,
                was_running=is_running,
                auto_start=is_running,  # Auto-start if was running
                created_at=existing.created_at if existing else now,
                last_updated=now,
                stats_snapshot=stats or {},
            )
            
            # Save all bots
            return self._save_all_bots()
            
        except Exception as e:
            logger.error(f"Error saving single bot: {e}")
            return False
    
    def delete_bot(self, bot_id: str) -> bool:
        """
        Remove a bot from saved configurations.
        
        Args:
            bot_id: Bot ID to remove
            
        Returns:
            True if deleted successfully
        """
        if bot_id in self._saved_bots:
            del self._saved_bots[bot_id]
            return self._save_all_bots()
        return False
    
    def _save_all_bots(self) -> bool:
        """Save all in-memory bot states to disk."""
        try:
            now = datetime.now().isoformat()
            
            bots_data = []
            for bot_state in self._saved_bots.values():
                bots_data.append(asdict(bot_state))
            
            data = {
                'version': 1,
                'saved_at': now,
                'bots_count': len(bots_data),
                'bots': bots_data,
            }
            
            with open(self._bots_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            try:
                os.chmod(self._bots_file, 0o600)
            except Exception:
                pass
            
            logger.debug(f"Saved {len(bots_data)} bots to disk")
            return True
            
        except Exception as e:
            logger.error(f"Error saving all bots: {e}")
            return False
    
    def get_saved_bot(self, bot_id: str) -> Optional[SavedBotState]:
        """Get a saved bot by ID."""
        return self._saved_bots.get(bot_id)
    
    def get_all_saved_bots(self) -> List[SavedBotState]:
        """Get all saved bots."""
        return list(self._saved_bots.values())
    
    def has_saved_bots(self) -> bool:
        """Check if there are any saved bots."""
        if self._saved_bots:
            return True
        # Check file on disk
        if self._bots_file.exists():
            try:
                with open(self._bots_file, 'r') as f:
                    data = json.load(f)
                return len(data.get('bots', [])) > 0
            except Exception:
                pass
        return False
    
    # =========================================================================
    # Position Tracking Persistence
    # =========================================================================
    
    def load_position_tracking(self) -> Dict[str, SavedPositionTracking]:
        """
        Load position tracking data from disk.
        
        Returns:
            Dict mapping "symbol@broker" to SavedPositionTracking
        """
        if not self._positions_file.exists():
            logger.debug("No position tracking file found")
            return {}
        
        try:
            with open(self._positions_file, 'r') as f:
                data = json.load(f)
            
            self._position_tracking.clear()
            
            for key, pos_data in data.get('positions', {}).items():
                try:
                    tracking = SavedPositionTracking(
                        symbol=pos_data.get('symbol', ''),
                        broker=pos_data.get('broker', ''),
                        bot_id=pos_data.get('bot_id', ''),
                        bot_name=pos_data.get('bot_name', ''),
                        opened_at=pos_data.get('opened_at'),
                        quantity=pos_data.get('quantity', 0.0),
                        synced=pos_data.get('synced', False),
                        strategy=pos_data.get('strategy'),
                    )
                    self._position_tracking[key] = tracking
                except Exception as e:
                    logger.error(f"Error loading position tracking entry: {e}")
            
            logger.info(f"Loaded {len(self._position_tracking)} position tracking entries")
            return self._position_tracking
            
        except Exception as e:
            logger.error(f"Error loading position tracking: {e}")
            return {}
    
    def save_position_tracking(self, positions: Dict[str, Dict]) -> bool:
        """
        Save position tracking data to disk.
        
        Args:
            positions: Dict mapping "symbol@broker" to position info dict with:
                       - bot_id, bot_name, opened_at, quantity, synced
                       
        Returns:
            True if saved successfully
        """
        try:
            now = datetime.now().isoformat()
            
            # Convert to serializable format
            positions_data = {}
            for key, info in positions.items():
                # Parse key to get symbol and broker
                parts = key.split('@')
                if len(parts) == 2:
                    symbol, broker = parts
                else:
                    symbol = key
                    broker = 'unknown'
                
                positions_data[key] = {
                    'symbol': symbol,
                    'broker': broker,
                    'bot_id': info.get('bot_id', ''),
                    'bot_name': info.get('bot_name', ''),
                    'opened_at': info.get('opened_at'),
                    'quantity': info.get('quantity', 0.0),
                    'synced': info.get('synced', False),
                    'strategy': info.get('strategy'),
                }
            
            data = {
                'version': 1,
                'saved_at': now,
                'positions_count': len(positions_data),
                'positions': positions_data,
            }
            
            with open(self._positions_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            try:
                os.chmod(self._positions_file, 0o600)
            except Exception:
                pass
            
            logger.debug(f"Saved {len(positions_data)} position tracking entries")
            return True
            
        except Exception as e:
            logger.error(f"Error saving position tracking: {e}")
            return False
    
    def clear_all(self) -> bool:
        """Clear all saved data (bots and positions)."""
        try:
            self._saved_bots.clear()
            self._position_tracking.clear()
            
            if self._bots_file.exists():
                self._bots_file.unlink()
            if self._positions_file.exists():
                self._positions_file.unlink()
            
            logger.info("Cleared all saved bot data")
            return True
        except Exception as e:
            logger.error(f"Error clearing saved data: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Get summary of saved data for API response."""
        return {
            'bots_count': len(self._saved_bots),
            'positions_count': len(self._position_tracking),
            'config_dir': str(self._config_dir),
            'bots_file_exists': self._bots_file.exists(),
            'positions_file_exists': self._positions_file.exists(),
            'bots': [
                {
                    'bot_id': bot.bot_id,
                    'name': bot.config.get('name', 'Unknown'),
                    'was_running': bot.was_running,
                    'auto_start': bot.auto_start,
                    'last_updated': bot.last_updated,
                }
                for bot in self._saved_bots.values()
            ],
        }


# Global instance
_saved_bots_manager: Optional[SavedBotsManager] = None


def get_saved_bots_manager() -> SavedBotsManager:
    """Get the global saved bots manager."""
    global _saved_bots_manager
    if _saved_bots_manager is None:
        _saved_bots_manager = SavedBotsManager()
    return _saved_bots_manager
