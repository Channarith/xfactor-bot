"""
Visual Strategy Builder Backend

Provides the data model and execution engine for drag-and-drop strategy building.
The frontend will provide the visual interface; this handles the logic.

Features:
- Node-based strategy definition
- Condition blocks (indicators, price action, time)
- Action blocks (buy, sell, modify position)
- Flow control (if/else, loops)
- Backtesting integration
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime
import json
import uuid

from loguru import logger


class NodeType(Enum):
    """Types of strategy builder nodes."""
    # Triggers
    TRIGGER_PRICE = "trigger_price"
    TRIGGER_INDICATOR = "trigger_indicator"
    TRIGGER_TIME = "trigger_time"
    TRIGGER_PATTERN = "trigger_pattern"
    
    # Conditions
    CONDITION_COMPARE = "condition_compare"
    CONDITION_AND = "condition_and"
    CONDITION_OR = "condition_or"
    CONDITION_NOT = "condition_not"
    
    # Actions
    ACTION_BUY = "action_buy"
    ACTION_SELL = "action_sell"
    ACTION_CLOSE = "action_close"
    ACTION_MODIFY_SL = "action_modify_sl"
    ACTION_MODIFY_TP = "action_modify_tp"
    ACTION_ALERT = "action_alert"
    
    # Flow Control
    FLOW_IF = "flow_if"
    FLOW_ELSE = "flow_else"
    FLOW_WAIT = "flow_wait"


class ComparisonOperator(Enum):
    """Comparison operators for conditions."""
    GREATER = ">"
    GREATER_EQUAL = ">="
    LESS = "<"
    LESS_EQUAL = "<="
    EQUAL = "=="
    NOT_EQUAL = "!="
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"


class IndicatorType(Enum):
    """Available indicators for strategy builder."""
    SMA = "sma"
    EMA = "ema"
    RSI = "rsi"
    MACD = "macd"
    MACD_SIGNAL = "macd_signal"
    MACD_HISTOGRAM = "macd_histogram"
    BOLLINGER_UPPER = "bb_upper"
    BOLLINGER_MIDDLE = "bb_middle"
    BOLLINGER_LOWER = "bb_lower"
    ATR = "atr"
    ADX = "adx"
    STOCHASTIC_K = "stoch_k"
    STOCHASTIC_D = "stoch_d"
    VWAP = "vwap"
    VOLUME = "volume"
    VOLUME_SMA = "volume_sma"


@dataclass
class NodeConnection:
    """Connection between two nodes."""
    from_node: str
    from_port: str
    to_node: str
    to_port: str


@dataclass
class NodePosition:
    """Visual position of a node."""
    x: float
    y: float


@dataclass
class StrategyNode:
    """A single node in the strategy builder."""
    id: str
    type: NodeType
    name: str
    position: NodePosition
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(cls, node_type: NodeType, name: str, x: float = 0, y: float = 0, config: Dict[str, Any] = None) -> 'StrategyNode':
        """Factory method to create a new node."""
        return cls(
            id=str(uuid.uuid4()),
            type=node_type,
            name=name,
            position=NodePosition(x, y),
            config=config or {},
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "position": {"x": self.position.x, "y": self.position.y},
            "inputs": self.inputs,
            "outputs": self.outputs,
            "config": self.config,
        }


@dataclass
class VisualStrategy:
    """A complete visual strategy definition."""
    id: str
    name: str
    description: str
    nodes: List[StrategyNode] = field(default_factory=list)
    connections: List[NodeConnection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_node(self, node: StrategyNode) -> None:
        """Add a node to the strategy."""
        self.nodes.append(node)
        self.updated_at = datetime.now()
    
    def remove_node(self, node_id: str) -> None:
        """Remove a node and its connections."""
        self.nodes = [n for n in self.nodes if n.id != node_id]
        self.connections = [c for c in self.connections 
                          if c.from_node != node_id and c.to_node != node_id]
        self.updated_at = datetime.now()
    
    def connect(self, from_node: str, from_port: str, to_node: str, to_port: str) -> None:
        """Create a connection between nodes."""
        self.connections.append(NodeConnection(from_node, from_port, to_node, to_port))
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes],
            "connections": [
                {
                    "from_node": c.from_node,
                    "from_port": c.from_port,
                    "to_node": c.to_node,
                    "to_port": c.to_port,
                }
                for c in self.connections
            ],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VisualStrategy':
        """Create a strategy from dictionary."""
        strategy = cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )
        
        for node_data in data.get("nodes", []):
            node = StrategyNode(
                id=node_data["id"],
                type=NodeType(node_data["type"]),
                name=node_data["name"],
                position=NodePosition(node_data["position"]["x"], node_data["position"]["y"]),
                inputs=node_data.get("inputs", {}),
                outputs=node_data.get("outputs", {}),
                config=node_data.get("config", {}),
            )
            strategy.nodes.append(node)
        
        for conn_data in data.get("connections", []):
            strategy.connections.append(NodeConnection(
                from_node=conn_data["from_node"],
                from_port=conn_data["from_port"],
                to_node=conn_data["to_node"],
                to_port=conn_data["to_port"],
            ))
        
        return strategy


class VisualStrategyEngine:
    """
    Executes visual strategies by evaluating nodes and connections.
    
    Usage:
        engine = VisualStrategyEngine()
        strategy = VisualStrategy(...)
        signals = engine.evaluate(strategy, price_data)
    """
    
    def __init__(self):
        self._strategies: Dict[str, VisualStrategy] = {}
        self._node_cache: Dict[str, Any] = {}
    
    def save_strategy(self, strategy: VisualStrategy) -> None:
        """Save a strategy."""
        self._strategies[strategy.id] = strategy
        logger.info(f"Saved visual strategy: {strategy.name}")
    
    def load_strategy(self, strategy_id: str) -> Optional[VisualStrategy]:
        """Load a strategy by ID."""
        return self._strategies.get(strategy_id)
    
    def list_strategies(self) -> List[Dict[str, Any]]:
        """List all saved strategies."""
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "node_count": len(s.nodes),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in self._strategies.values()
        ]
    
    def delete_strategy(self, strategy_id: str) -> bool:
        """Delete a strategy."""
        if strategy_id in self._strategies:
            del self._strategies[strategy_id]
            return True
        return False
    
    def evaluate(
        self,
        strategy: VisualStrategy,
        price_data: Dict[str, Any],
        position: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate a visual strategy against current market data.
        
        Args:
            strategy: The visual strategy to evaluate
            price_data: Current price data (OHLCV + indicators)
            position: Current position info (if any)
        
        Returns:
            Dictionary with signals and actions
        """
        self._node_cache = {}
        signals = {
            "should_buy": False,
            "should_sell": False,
            "should_close": False,
            "alerts": [],
            "modifications": [],
            "evaluated_nodes": [],
        }
        
        # Build node lookup
        nodes_by_id = {n.id: n for n in strategy.nodes}
        
        # Find entry point nodes (triggers)
        trigger_nodes = [n for n in strategy.nodes if n.type.value.startswith("trigger_")]
        
        # Evaluate each trigger
        for trigger in trigger_nodes:
            result = self._evaluate_node(trigger, nodes_by_id, strategy.connections, price_data, position)
            signals["evaluated_nodes"].append({
                "node_id": trigger.id,
                "name": trigger.name,
                "result": result,
            })
            
            # Follow connections from this trigger if it fired
            if result:
                self._follow_connections(trigger.id, nodes_by_id, strategy.connections, price_data, position, signals)
        
        return signals
    
    def _evaluate_node(
        self,
        node: StrategyNode,
        nodes_by_id: Dict[str, StrategyNode],
        connections: List[NodeConnection],
        price_data: Dict[str, Any],
        position: Optional[Dict[str, Any]],
    ) -> Any:
        """Evaluate a single node."""
        # Check cache
        if node.id in self._node_cache:
            return self._node_cache[node.id]
        
        result = False
        
        if node.type == NodeType.TRIGGER_PRICE:
            result = self._evaluate_price_trigger(node, price_data)
        elif node.type == NodeType.TRIGGER_INDICATOR:
            result = self._evaluate_indicator_trigger(node, price_data)
        elif node.type == NodeType.CONDITION_COMPARE:
            result = self._evaluate_comparison(node, price_data)
        elif node.type == NodeType.CONDITION_AND:
            result = self._evaluate_and(node, nodes_by_id, connections, price_data, position)
        elif node.type == NodeType.CONDITION_OR:
            result = self._evaluate_or(node, nodes_by_id, connections, price_data, position)
        # Actions return True to indicate they should execute
        elif node.type in [NodeType.ACTION_BUY, NodeType.ACTION_SELL, NodeType.ACTION_CLOSE]:
            result = True
        
        self._node_cache[node.id] = result
        return result
    
    def _evaluate_price_trigger(self, node: StrategyNode, price_data: Dict[str, Any]) -> bool:
        """Evaluate a price-based trigger."""
        config = node.config
        operator = ComparisonOperator(config.get("operator", ">"))
        value = config.get("value", 0)
        price_field = config.get("price_field", "close")
        
        current_price = price_data.get(price_field, 0)
        
        return self._compare(current_price, operator, value, price_data)
    
    def _evaluate_indicator_trigger(self, node: StrategyNode, price_data: Dict[str, Any]) -> bool:
        """Evaluate an indicator-based trigger."""
        config = node.config
        indicator = config.get("indicator", "rsi")
        operator = ComparisonOperator(config.get("operator", ">"))
        value = config.get("value", 50)
        
        indicator_value = price_data.get(indicator, 0)
        
        return self._compare(indicator_value, operator, value, price_data)
    
    def _evaluate_comparison(self, node: StrategyNode, price_data: Dict[str, Any]) -> bool:
        """Evaluate a comparison condition."""
        config = node.config
        left = config.get("left", "close")
        operator = ComparisonOperator(config.get("operator", ">"))
        right = config.get("right", 0)
        
        left_value = price_data.get(left, left) if isinstance(left, str) else left
        right_value = price_data.get(right, right) if isinstance(right, str) else right
        
        return self._compare(left_value, operator, right_value, price_data)
    
    def _evaluate_and(
        self,
        node: StrategyNode,
        nodes_by_id: Dict[str, StrategyNode],
        connections: List[NodeConnection],
        price_data: Dict[str, Any],
        position: Optional[Dict[str, Any]],
    ) -> bool:
        """Evaluate AND condition - all inputs must be true."""
        input_connections = [c for c in connections if c.to_node == node.id]
        
        if not input_connections:
            return False
        
        for conn in input_connections:
            input_node = nodes_by_id.get(conn.from_node)
            if input_node:
                if not self._evaluate_node(input_node, nodes_by_id, connections, price_data, position):
                    return False
        return True
    
    def _evaluate_or(
        self,
        node: StrategyNode,
        nodes_by_id: Dict[str, StrategyNode],
        connections: List[NodeConnection],
        price_data: Dict[str, Any],
        position: Optional[Dict[str, Any]],
    ) -> bool:
        """Evaluate OR condition - any input must be true."""
        input_connections = [c for c in connections if c.to_node == node.id]
        
        for conn in input_connections:
            input_node = nodes_by_id.get(conn.from_node)
            if input_node:
                if self._evaluate_node(input_node, nodes_by_id, connections, price_data, position):
                    return True
        return False
    
    def _compare(
        self,
        left: Any,
        operator: ComparisonOperator,
        right: Any,
        price_data: Dict[str, Any],
    ) -> bool:
        """Perform comparison operation."""
        if operator == ComparisonOperator.GREATER:
            return left > right
        elif operator == ComparisonOperator.GREATER_EQUAL:
            return left >= right
        elif operator == ComparisonOperator.LESS:
            return left < right
        elif operator == ComparisonOperator.LESS_EQUAL:
            return left <= right
        elif operator == ComparisonOperator.EQUAL:
            return left == right
        elif operator == ComparisonOperator.NOT_EQUAL:
            return left != right
        elif operator == ComparisonOperator.CROSSES_ABOVE:
            # Need previous values
            prev_left = price_data.get("prev_" + str(left), left)
            return prev_left <= right and left > right
        elif operator == ComparisonOperator.CROSSES_BELOW:
            prev_left = price_data.get("prev_" + str(left), left)
            return prev_left >= right and left < right
        
        return False
    
    def _follow_connections(
        self,
        from_node_id: str,
        nodes_by_id: Dict[str, StrategyNode],
        connections: List[NodeConnection],
        price_data: Dict[str, Any],
        position: Optional[Dict[str, Any]],
        signals: Dict[str, Any],
    ) -> None:
        """Follow connections from a node and execute actions."""
        output_connections = [c for c in connections if c.from_node == from_node_id]
        
        for conn in output_connections:
            target_node = nodes_by_id.get(conn.to_node)
            if not target_node:
                continue
            
            # Handle action nodes
            if target_node.type == NodeType.ACTION_BUY:
                signals["should_buy"] = True
            elif target_node.type == NodeType.ACTION_SELL:
                signals["should_sell"] = True
            elif target_node.type == NodeType.ACTION_CLOSE:
                signals["should_close"] = True
            elif target_node.type == NodeType.ACTION_ALERT:
                signals["alerts"].append(target_node.config.get("message", "Alert triggered"))
            
            # Continue following connections
            self._follow_connections(target_node.id, nodes_by_id, connections, price_data, position, signals)


# Singleton engine
_engine: Optional[VisualStrategyEngine] = None


def get_visual_strategy_engine() -> VisualStrategyEngine:
    """Get or create the visual strategy engine singleton."""
    global _engine
    if _engine is None:
        _engine = VisualStrategyEngine()
    return _engine


# Node templates for the frontend
NODE_TEMPLATES = {
    "triggers": [
        {"type": "trigger_price", "name": "Price Trigger", "description": "Trigger when price meets condition"},
        {"type": "trigger_indicator", "name": "Indicator Trigger", "description": "Trigger on indicator value"},
        {"type": "trigger_time", "name": "Time Trigger", "description": "Trigger at specific time"},
        {"type": "trigger_pattern", "name": "Pattern Trigger", "description": "Trigger on candlestick pattern"},
    ],
    "conditions": [
        {"type": "condition_compare", "name": "Compare", "description": "Compare two values"},
        {"type": "condition_and", "name": "AND", "description": "All conditions must be true"},
        {"type": "condition_or", "name": "OR", "description": "Any condition must be true"},
        {"type": "condition_not", "name": "NOT", "description": "Invert condition"},
    ],
    "actions": [
        {"type": "action_buy", "name": "Buy", "description": "Open long position"},
        {"type": "action_sell", "name": "Sell", "description": "Open short position"},
        {"type": "action_close", "name": "Close", "description": "Close position"},
        {"type": "action_modify_sl", "name": "Modify SL", "description": "Adjust stop loss"},
        {"type": "action_modify_tp", "name": "Modify TP", "description": "Adjust take profit"},
        {"type": "action_alert", "name": "Alert", "description": "Send notification"},
    ],
    "flow": [
        {"type": "flow_if", "name": "If", "description": "Conditional branch"},
        {"type": "flow_else", "name": "Else", "description": "Alternate branch"},
        {"type": "flow_wait", "name": "Wait", "description": "Wait for condition"},
    ],
}

