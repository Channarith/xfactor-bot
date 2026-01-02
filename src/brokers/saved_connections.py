"""
Saved Broker Connections Manager.

Stores broker connection configurations securely for:
- Auto-connect on startup
- Quick reconnection
- Multiple saved connections per broker type

Security: Credentials are stored encrypted using Fernet symmetric encryption.
The encryption key is derived from a machine-specific identifier.
"""

import json
import os
import base64
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from loguru import logger

try:
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    logger.warning("cryptography not installed - credentials will be stored in plain text")


@dataclass
class SavedConnection:
    """A saved broker connection configuration."""
    id: str
    broker_type: str
    name: str  # User-friendly name like "My Paper Account"
    config: Dict[str, Any]  # Connection config (encrypted sensitive fields)
    created_at: str
    last_used: Optional[str] = None
    auto_connect: bool = False
    is_default: bool = False


class SavedConnectionsManager:
    """
    Manages saved broker connection configurations.
    
    Stores configurations in a JSON file with encrypted credentials.
    """
    
    # Fields that should be encrypted
    SENSITIVE_FIELDS = {'api_key', 'secret_key', 'password', 'refresh_token', 'access_token'}
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the saved connections manager.
        
        Args:
            config_dir: Directory to store configuration files.
                       Defaults to ~/.xfactor-bot/
        """
        if config_dir:
            self._config_dir = Path(config_dir)
        else:
            # Use home directory for persistent storage
            self._config_dir = Path.home() / ".xfactor-bot"
        
        self._config_file = self._config_dir / "saved_connections.json"
        self._connections: Dict[str, SavedConnection] = {}
        self._fernet: Optional[Fernet] = None
        
        # Initialize
        self._ensure_config_dir()
        self._init_encryption()
        self._load_connections()
    
    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        
        # Set restrictive permissions on Unix
        try:
            os.chmod(self._config_dir, 0o700)
        except Exception:
            pass
    
    def _init_encryption(self):
        """Initialize encryption using a machine-specific key."""
        if not ENCRYPTION_AVAILABLE:
            return
        
        try:
            # Generate a key based on machine identifier
            # This ensures credentials are tied to this machine
            key_material = self._get_machine_id()
            
            # Derive a Fernet key from the machine ID
            key = base64.urlsafe_b64encode(
                hashlib.sha256(key_material.encode()).digest()
            )
            self._fernet = Fernet(key)
            logger.debug("Encryption initialized for saved connections")
        except Exception as e:
            logger.warning(f"Could not initialize encryption: {e}")
            self._fernet = None
    
    def _get_machine_id(self) -> str:
        """Get a unique machine identifier for key derivation."""
        identifiers = []
        
        # Try various methods to get a unique machine ID
        try:
            # macOS/Linux
            if os.path.exists('/etc/machine-id'):
                with open('/etc/machine-id', 'r') as f:
                    identifiers.append(f.read().strip())
        except Exception:
            pass
        
        try:
            # macOS hardware UUID
            import subprocess
            result = subprocess.run(
                ['system_profiler', 'SPHardwareDataType'],
                capture_output=True, text=True, timeout=5
            )
            if 'Hardware UUID' in result.stdout:
                for line in result.stdout.split('\n'):
                    if 'Hardware UUID' in line:
                        identifiers.append(line.split(':')[1].strip())
                        break
        except Exception:
            pass
        
        # Fallback: use username and hostname
        import socket
        identifiers.append(f"{os.getenv('USER', 'user')}@{socket.gethostname()}")
        
        # Combine all identifiers
        return '|'.join(identifiers) + "|xfactor-bot-v1"
    
    def _encrypt(self, value: str) -> str:
        """Encrypt a string value."""
        if not self._fernet or not value:
            return value
        try:
            return self._fernet.encrypt(value.encode()).decode()
        except Exception:
            return value
    
    def _decrypt(self, value: str) -> str:
        """Decrypt a string value."""
        if not self._fernet or not value:
            return value
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except Exception:
            # May be unencrypted (legacy) or corrupted
            return value
    
    def _encrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in a config dict."""
        encrypted = config.copy()
        for field in self.SENSITIVE_FIELDS:
            if field in encrypted and encrypted[field]:
                encrypted[field] = self._encrypt(str(encrypted[field]))
        return encrypted
    
    def _decrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in a config dict."""
        decrypted = config.copy()
        for field in self.SENSITIVE_FIELDS:
            if field in decrypted and decrypted[field]:
                decrypted[field] = self._decrypt(str(decrypted[field]))
        return decrypted
    
    def _load_connections(self):
        """Load saved connections from disk."""
        if not self._config_file.exists():
            logger.debug("No saved connections file found")
            return
        
        try:
            with open(self._config_file, 'r') as f:
                data = json.load(f)
            
            for conn_data in data.get('connections', []):
                conn = SavedConnection(**conn_data)
                self._connections[conn.id] = conn
            
            logger.info(f"Loaded {len(self._connections)} saved broker connections")
            
        except Exception as e:
            logger.error(f"Error loading saved connections: {e}")
    
    def _save_connections(self):
        """Save connections to disk."""
        try:
            data = {
                'version': 1,
                'updated_at': datetime.now().isoformat(),
                'connections': [asdict(c) for c in self._connections.values()]
            }
            
            with open(self._config_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Set restrictive permissions
            try:
                os.chmod(self._config_file, 0o600)
            except Exception:
                pass
            
            logger.debug(f"Saved {len(self._connections)} broker connections")
            
        except Exception as e:
            logger.error(f"Error saving connections: {e}")
    
    def save_connection(
        self,
        broker_type: str,
        config: Dict[str, Any],
        name: Optional[str] = None,
        auto_connect: bool = False,
        set_as_default: bool = False,
    ) -> SavedConnection:
        """
        Save a broker connection configuration.
        
        Args:
            broker_type: Type of broker (alpaca, ibkr, etc.)
            config: Connection configuration dict
            name: User-friendly name for the connection
            auto_connect: Whether to auto-connect on startup
            set_as_default: Set as default connection for this broker
            
        Returns:
            The saved connection object
        """
        import uuid
        
        # Generate ID
        conn_id = f"{broker_type}_{uuid.uuid4().hex[:8]}"
        
        # Generate name if not provided
        if not name:
            paper = config.get('paper', True)
            name = f"{broker_type.upper()} {'Paper' if paper else 'Live'}"
        
        # Encrypt sensitive fields
        encrypted_config = self._encrypt_config(config)
        
        # If setting as default, unset other defaults for this broker
        if set_as_default:
            for conn in self._connections.values():
                if conn.broker_type == broker_type:
                    conn.is_default = False
        
        # Create connection object
        connection = SavedConnection(
            id=conn_id,
            broker_type=broker_type,
            name=name,
            config=encrypted_config,
            created_at=datetime.now().isoformat(),
            last_used=datetime.now().isoformat(),
            auto_connect=auto_connect,
            is_default=set_as_default,
        )
        
        self._connections[conn_id] = connection
        self._save_connections()
        
        logger.info(f"Saved broker connection: {name} ({broker_type})")
        
        return connection
    
    def update_connection(
        self,
        conn_id: str,
        name: Optional[str] = None,
        auto_connect: Optional[bool] = None,
        set_as_default: Optional[bool] = None,
    ) -> Optional[SavedConnection]:
        """Update a saved connection's settings."""
        if conn_id not in self._connections:
            return None
        
        conn = self._connections[conn_id]
        
        if name is not None:
            conn.name = name
        if auto_connect is not None:
            conn.auto_connect = auto_connect
        if set_as_default is not None:
            if set_as_default:
                # Unset other defaults for this broker
                for c in self._connections.values():
                    if c.broker_type == conn.broker_type:
                        c.is_default = False
            conn.is_default = set_as_default
        
        self._save_connections()
        return conn
    
    def delete_connection(self, conn_id: str) -> bool:
        """Delete a saved connection."""
        if conn_id in self._connections:
            del self._connections[conn_id]
            self._save_connections()
            logger.info(f"Deleted saved connection: {conn_id}")
            return True
        return False
    
    def get_connection(self, conn_id: str) -> Optional[SavedConnection]:
        """Get a saved connection by ID."""
        return self._connections.get(conn_id)
    
    def get_connection_config(self, conn_id: str) -> Optional[Dict[str, Any]]:
        """Get decrypted config for a saved connection."""
        conn = self._connections.get(conn_id)
        if conn:
            return self._decrypt_config(conn.config)
        return None
    
    def get_connections_by_broker(self, broker_type: str) -> List[SavedConnection]:
        """Get all saved connections for a broker type."""
        return [c for c in self._connections.values() if c.broker_type == broker_type]
    
    def get_all_connections(self) -> List[SavedConnection]:
        """Get all saved connections."""
        return list(self._connections.values())
    
    def get_auto_connect_connections(self) -> List[SavedConnection]:
        """Get connections marked for auto-connect."""
        return [c for c in self._connections.values() if c.auto_connect]
    
    def get_default_connection(self, broker_type: str) -> Optional[SavedConnection]:
        """Get the default connection for a broker type."""
        for conn in self._connections.values():
            if conn.broker_type == broker_type and conn.is_default:
                return conn
        return None
    
    def mark_used(self, conn_id: str):
        """Update last_used timestamp for a connection."""
        if conn_id in self._connections:
            self._connections[conn_id].last_used = datetime.now().isoformat()
            self._save_connections()
    
    def to_dict(self) -> Dict[str, Any]:
        """Get all connections as a dictionary (safe for API response)."""
        connections = []
        for conn in self._connections.values():
            # Don't include actual credentials in API response
            conn_dict = asdict(conn)
            # Mask sensitive fields
            for field in self.SENSITIVE_FIELDS:
                if field in conn_dict.get('config', {}):
                    value = conn_dict['config'][field]
                    if value:
                        conn_dict['config'][field] = value[:4] + '****' if len(value) > 4 else '****'
            connections.append(conn_dict)
        
        return {
            'connections': connections,
            'count': len(connections),
            'encryption_enabled': ENCRYPTION_AVAILABLE and self._fernet is not None,
        }


# Global instance
_saved_connections: Optional[SavedConnectionsManager] = None


def get_saved_connections() -> SavedConnectionsManager:
    """Get the global saved connections manager."""
    global _saved_connections
    if _saved_connections is None:
        _saved_connections = SavedConnectionsManager()
    return _saved_connections

