"""
Phase 14: Multi-Exchange Integration System
Unified interface for trading across multiple cryptocurrency exchanges
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid
from decimal import Decimal
import numpy as np
from abc import ABC, abstractmethod

from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

class ExchangeType(Enum):
    """Exchange types"""
    CENTRALIZED = "centralized"
    DECENTRALIZED = "decentralized"
    DERIVATIVES = "derivatives"
    SPOT = "spot"

class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    OCO = "oco"  # One Cancels Other
    ICEBERG = "iceberg"

class ExchangeStatus(Enum):
    """Exchange connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class ExchangeConfig:
    """Exchange configuration"""
    exchange_id: str
    name: str
    type: ExchangeType
    api_endpoint: str
    websocket_endpoint: str
    supported_symbols: List[str]
    trading_fees: Dict[str, float]
    withdrawal_fees: Dict[str, float]
    min_order_sizes: Dict[str, float]
    rate_limits: Dict[str, int]
    supports_margin: bool = False
    supports_futures: bool = False
    supports_options: bool = False

@dataclass
class MarketData:
    """Market data structure"""
    symbol: str
    exchange: str
    price: Decimal
    bid: Decimal
    ask: Decimal
    volume_24h: Decimal
    timestamp: datetime
    metadata: Dict[str, Any] = None

@dataclass
class OrderBook:
    """Order book structure"""
    symbol: str
    exchange: str
    bids: List[Tuple[Decimal, Decimal]]  # price, quantity
    asks: List[Tuple[Decimal, Decimal]]  # price, quantity
    timestamp: datetime

@dataclass
class Trade:
    """Trade structure"""
    trade_id: str
    symbol: str
    exchange: str
    side: str
    amount: Decimal
    price: Decimal
    timestamp: datetime
    fee: Decimal
    fee_currency: str

@dataclass
class Balance:
    """Account balance structure"""
    currency: str
    exchange: str
    available: Decimal
    locked: Decimal
    total: Decimal
    last_updated: datetime

@dataclass
class ArbitrageOpportunity:
    """Arbitrage opportunity structure"""
    opportunity_id: str
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: Decimal
    sell_price: Decimal
    spread: Decimal
    spread_percentage: float
    potential_profit: Decimal
    confidence: float
    valid_until: datetime
    required_capital: Decimal

class BaseExchangeConnector(ABC):
    """Base class for exchange connectors"""
    
    def __init__(self, config: ExchangeConfig):
        self.config = config
        self.status = ExchangeStatus.DISCONNECTED
        self.last_heartbeat = None
        self.rate_limiter = {}
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to exchange"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from exchange"""
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get current market data"""
        pass
    
    @abstractmethod
    async def get_order_book(self, symbol: str, depth: int = 10) -> Optional[OrderBook]:
        """Get order book"""
        pass
    
    @abstractmethod
    async def place_order(self, symbol: str, side: str, amount: Decimal, 
                         price: Optional[Decimal] = None, order_type: OrderType = OrderType.MARKET) -> str:
        """Place order"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status"""
        pass
    
    @abstractmethod
    async def get_balances(self) -> List[Balance]:
        """Get account balances"""
        pass
    
    @abstractmethod
    async def get_trade_history(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Get trade history"""
        pass

class BinanceConnector(BaseExchangeConnector):
    """Binance exchange connector"""
    
    async def connect(self) -> bool:
        """Connect to Binance"""
        try:
            # Initialize Binance connection
            self.status = ExchangeStatus.CONNECTING
            
            # Mock connection logic
            await asyncio.sleep(1)
            
            self.status = ExchangeStatus.CONNECTED
            self.last_heartbeat = datetime.now(timezone.utc)
            
            logger.info(f"Connected to {self.config.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.config.name}: {e}")
            self.status = ExchangeStatus.ERROR
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Binance"""
        self.status = ExchangeStatus.DISCONNECTED
        return True
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get Binance market data"""
        try:
            # Mock market data
            return MarketData(
                symbol=symbol,
                exchange=self.config.exchange_id,
                price=Decimal("45000.00"),
                bid=Decimal("44995.00"),
                ask=Decimal("45005.00"),
                volume_24h=Decimal("1000000"),
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Error getting market data from {self.config.name}: {e}")
            return None
    
    async def get_order_book(self, symbol: str, depth: int = 10) -> Optional[OrderBook]:
        """Get Binance order book"""
        try:
            # Mock order book
            bids = [(Decimal("44990.00"), Decimal("1.5")) for _ in range(depth)]
            asks = [(Decimal("45010.00"), Decimal("1.2")) for _ in range(depth)]
            
            return OrderBook(
                symbol=symbol,
                exchange=self.config.exchange_id,
                bids=bids,
                asks=asks,
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Error getting order book from {self.config.name}: {e}")
            return None
    
    async def place_order(self, symbol: str, side: str, amount: Decimal, 
                         price: Optional[Decimal] = None, order_type: OrderType = OrderType.MARKET) -> str:
        """Place order on Binance"""
        try:
            order_id = f"binance_{uuid.uuid4()}"
            logger.info(f"Placed {order_type.value} {side} order for {amount} {symbol} on {self.config.name}")
            return order_id
        except Exception as e:
            logger.error(f"Error placing order on {self.config.name}: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order on Binance"""
        try:
            logger.info(f"Cancelled order {order_id} on {self.config.name}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order on {self.config.name}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status from Binance"""
        try:
            return {
                "order_id": order_id,
                "status": "filled",
                "filled_amount": "1.0",
                "avg_price": "45000.00"
            }
        except Exception as e:
            logger.error(f"Error getting order status from {self.config.name}: {e}")
            return {}
    
    async def get_balances(self) -> List[Balance]:
        """Get Binance balances"""
        try:
            return [
                Balance(
                    currency="BTC",
                    exchange=self.config.exchange_id,
                    available=Decimal("1.5"),
                    locked=Decimal("0.1"),
                    total=Decimal("1.6"),
                    last_updated=datetime.now(timezone.utc)
                ),
                Balance(
                    currency="USD",
                    exchange=self.config.exchange_id,
                    available=Decimal("10000.00"),
                    locked=Decimal("1000.00"),
                    total=Decimal("11000.00"),
                    last_updated=datetime.now(timezone.utc)
                )
            ]
        except Exception as e:
            logger.error(f"Error getting balances from {self.config.name}: {e}")
            return []
    
    async def get_trade_history(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Get Binance trade history"""
        try:
            trades = []
            for i in range(min(limit, 5)):  # Mock 5 trades
                trades.append(Trade(
                    trade_id=f"trade_{i}",
                    symbol=symbol,
                    exchange=self.config.exchange_id,
                    side="buy" if i % 2 == 0 else "sell",
                    amount=Decimal("0.1"),
                    price=Decimal("45000.00"),
                    timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                    fee=Decimal("0.001"),
                    fee_currency="BTC"
                ))
            return trades
        except Exception as e:
            logger.error(f"Error getting trade history from {self.config.name}: {e}")
            return []

class CoinbaseConnector(BaseExchangeConnector):
    """Coinbase Pro exchange connector"""
    
    async def connect(self) -> bool:
        """Connect to Coinbase Pro"""
        try:
            self.status = ExchangeStatus.CONNECTING
            await asyncio.sleep(1)  # Mock connection delay
            self.status = ExchangeStatus.CONNECTED
            self.last_heartbeat = datetime.now(timezone.utc)
            logger.info(f"Connected to {self.config.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.config.name}: {e}")
            self.status = ExchangeStatus.ERROR
            return False
    
    async def disconnect(self) -> bool:
        self.status = ExchangeStatus.DISCONNECTED
        return True
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        # Mock Coinbase market data with slightly different prices
        try:
            return MarketData(
                symbol=symbol,
                exchange=self.config.exchange_id,
                price=Decimal("45020.00"),  # Slightly higher than Binance
                bid=Decimal("45015.00"),
                ask=Decimal("45025.00"),
                volume_24h=Decimal("800000"),
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Error getting market data from {self.config.name}: {e}")
            return None
    
    # Similar implementations for other methods...
    async def get_order_book(self, symbol: str, depth: int = 10) -> Optional[OrderBook]:
        try:
            bids = [(Decimal("45010.00"), Decimal("1.3")) for _ in range(depth)]
            asks = [(Decimal("45030.00"), Decimal("1.1")) for _ in range(depth)]
            
            return OrderBook(
                symbol=symbol,
                exchange=self.config.exchange_id,
                bids=bids,
                asks=asks,
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Error getting order book from {self.config.name}: {e}")
            return None
    
    async def place_order(self, symbol: str, side: str, amount: Decimal, 
                         price: Optional[Decimal] = None, order_type: OrderType = OrderType.MARKET) -> str:
        try:
            order_id = f"coinbase_{uuid.uuid4()}"
            logger.info(f"Placed {order_type.value} {side} order for {amount} {symbol} on {self.config.name}")
            return order_id
        except Exception as e:
            logger.error(f"Error placing order on {self.config.name}: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        try:
            logger.info(f"Cancelled order {order_id} on {self.config.name}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order on {self.config.name}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        try:
            return {
                "order_id": order_id,
                "status": "filled",
                "filled_amount": "1.0",
                "avg_price": "45020.00"
            }
        except Exception as e:
            logger.error(f"Error getting order status from {self.config.name}: {e}")
            return {}
    
    async def get_balances(self) -> List[Balance]:
        try:
            return [
                Balance(
                    currency="BTC",
                    exchange=self.config.exchange_id,
                    available=Decimal("1.2"),
                    locked=Decimal("0.05"),
                    total=Decimal("1.25"),
                    last_updated=datetime.now(timezone.utc)
                ),
                Balance(
                    currency="USD",
                    exchange=self.config.exchange_id,
                    available=Decimal("8000.00"),
                    locked=Decimal("500.00"),
                    total=Decimal("8500.00"),
                    last_updated=datetime.now(timezone.utc)
                )
            ]
        except Exception as e:
            logger.error(f"Error getting balances from {self.config.name}: {e}")
            return []
    
    async def get_trade_history(self, symbol: str, limit: int = 100) -> List[Trade]:
        try:
            trades = []
            for i in range(min(limit, 5)):
                trades.append(Trade(
                    trade_id=f"cb_trade_{i}",
                    symbol=symbol,
                    exchange=self.config.exchange_id,
                    side="buy" if i % 2 == 0 else "sell",
                    amount=Decimal("0.1"),
                    price=Decimal("45020.00"),
                    timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                    fee=Decimal("0.0025"),
                    fee_currency="USD"
                ))
            return trades
        except Exception as e:
            logger.error(f"Error getting trade history from {self.config.name}: {e}")
            return []

class MultiExchangeIntegration:
    """
    Multi-exchange integration system
    Phase 14: Unified interface for trading across multiple exchanges
    """
    
    def __init__(self):
        self.registry = get_registry()
        
        # Service dependencies
        self.event_service = None
        self.risk_service = None
        
        # Exchange management
        self.exchanges: Dict[str, BaseExchangeConnector] = {}
        self.exchange_configs: Dict[str, ExchangeConfig] = {}
        
        # Market data aggregation
        self.aggregated_market_data: Dict[str, Dict[str, MarketData]] = {}
        self.order_books: Dict[str, Dict[str, OrderBook]] = {}
        
        # Arbitrage tracking
        self.arbitrage_opportunities: List[ArbitrageOpportunity] = []
        self.arbitrage_history: List[Dict[str, Any]] = []
        
        # Unified balances
        self.unified_balances: Dict[str, List[Balance]] = {}
        
        # Performance metrics
        self.integration_metrics = {
            'connected_exchanges': 0,
            'total_volume_24h': Decimal("0"),
            'arbitrage_opportunities_found': 0,
            'successful_arbitrage_trades': 0,
            'cross_exchange_orders': 0,
            'data_latency_avg': 0.0
        }
        
        logger.info("MultiExchangeIntegration Phase 14 initialized")
    
    async def initialize(self):
        """Initialize multi-exchange integration"""
        try:
            # Get required services
            self.event_service = self.registry.get_service("wallet_event_streaming_service")
            self.risk_service = self.registry.get_service("risk_management_service")
            
            # Initialize exchange configurations
            await self._initialize_exchange_configs()
            
            # Connect to exchanges
            await self._connect_to_exchanges()
            
            # Start background tasks
            asyncio.create_task(self._market_data_aggregation_loop())
            asyncio.create_task(self._arbitrage_detection_loop())
            asyncio.create_task(self._balance_synchronization_loop())
            asyncio.create_task(self._health_monitoring_loop())
            asyncio.create_task(self._performance_tracking_loop())
            
            logger.info("MultiExchangeIntegration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MultiExchangeIntegration: {e}")
            raise
    
    async def _initialize_exchange_configs(self):
        """Initialize exchange configurations"""
        try:
            configs = {
                "binance": ExchangeConfig(
                    exchange_id="binance",
                    name="Binance",
                    type=ExchangeType.CENTRALIZED,
                    api_endpoint="https://api.binance.com",
                    websocket_endpoint="wss://stream.binance.com:9443",
                    supported_symbols=["BTC-USDT", "ETH-USDT", "SOL-USDT", "AVAX-USDT"],
                    trading_fees={"maker": 0.001, "taker": 0.001},
                    withdrawal_fees={"BTC": 0.0005, "ETH": 0.005},
                    min_order_sizes={"BTC": 0.00001, "ETH": 0.0001},
                    rate_limits={"requests_per_minute": 1200, "orders_per_second": 10},
                    supports_margin=True,
                    supports_futures=True
                ),
                
                "coinbase": ExchangeConfig(
                    exchange_id="coinbase",
                    name="Coinbase Pro",
                    type=ExchangeType.CENTRALIZED,
                    api_endpoint="https://api.pro.coinbase.com",
                    websocket_endpoint="wss://ws-feed.pro.coinbase.com",
                    supported_symbols=["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD"],
                    trading_fees={"maker": 0.005, "taker": 0.005},
                    withdrawal_fees={"BTC": 0.001, "ETH": 0.01},
                    min_order_sizes={"BTC": 0.001, "ETH": 0.01},
                    rate_limits={"requests_per_minute": 600, "orders_per_second": 5}
                ),
                
                "kraken": ExchangeConfig(
                    exchange_id="kraken",
                    name="Kraken",
                    type=ExchangeType.CENTRALIZED,
                    api_endpoint="https://api.kraken.com",
                    websocket_endpoint="wss://ws.kraken.com",
                    supported_symbols=["BTC-USD", "ETH-USD", "SOL-USD"],
                    trading_fees={"maker": 0.0016, "taker": 0.0026},
                    withdrawal_fees={"BTC": 0.00015, "ETH": 0.0025},
                    min_order_sizes={"BTC": 0.0001, "ETH": 0.001},
                    rate_limits={"requests_per_minute": 300, "orders_per_second": 3}
                )
            }
            
            self.exchange_configs = configs
            logger.info(f"Initialized {len(configs)} exchange configurations")
            
        except Exception as e:
            logger.error(f"Failed to initialize exchange configs: {e}")
            raise
    
    async def _connect_to_exchanges(self):
        """Connect to all configured exchanges"""
        try:
            connection_tasks = []
            
            for exchange_id, config in self.exchange_configs.items():
                if exchange_id == "binance":
                    connector = BinanceConnector(config)
                elif exchange_id == "coinbase":
                    connector = CoinbaseConnector(config)
                else:
                    # Generic connector for other exchanges
                    continue
                
                self.exchanges[exchange_id] = connector
                connection_tasks.append(connector.connect())
            
            # Connect to all exchanges concurrently
            results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            connected_count = 0
            for i, result in enumerate(results):
                exchange_id = list(self.exchange_configs.keys())[i]
                if result is True:
                    connected_count += 1
                    logger.info(f"Successfully connected to {exchange_id}")
                else:
                    logger.error(f"Failed to connect to {exchange_id}: {result}")
            
            self.integration_metrics['connected_exchanges'] = connected_count
            logger.info(f"Connected to {connected_count}/{len(self.exchange_configs)} exchanges")
            
        except Exception as e:
            logger.error(f"Failed to connect to exchanges: {e}")
            raise
    
    async def _market_data_aggregation_loop(self):
        """Aggregate market data from all exchanges"""
        while True:
            try:
                await asyncio.sleep(5)  # Update every 5 seconds
                
                for symbol in ["BTC-USD", "ETH-USD", "SOL-USD"]:
                    symbol_data = {}
                    
                    # Collect data from all connected exchanges
                    for exchange_id, connector in self.exchanges.items():
                        if connector.status == ExchangeStatus.CONNECTED:
                            try:
                                market_data = await connector.get_market_data(symbol)
                                if market_data:
                                    symbol_data[exchange_id] = market_data
                            except Exception as e:
                                logger.error(f"Error getting market data from {exchange_id}: {e}")
                    
                    if symbol_data:
                        self.aggregated_market_data[symbol] = symbol_data
                        
                        # Emit aggregated market data event
                        if self.event_service:
                            await self.event_service.emit_event({
                                'event_type': 'market.aggregated_data',
                                'symbol': symbol,
                                'exchanges': list(symbol_data.keys()),
                                'best_bid': max(data.bid for data in symbol_data.values()),
                                'best_ask': min(data.ask for data in symbol_data.values()),
                                'timestamp': datetime.now(timezone.utc).isoformat()
                            })
                
            except Exception as e:
                logger.error(f"Error in market data aggregation loop: {e}")
    
    async def _arbitrage_detection_loop(self):
        """Detect arbitrage opportunities across exchanges"""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                current_opportunities = []
                
                for symbol, exchange_data in self.aggregated_market_data.items():
                    if len(exchange_data) < 2:
                        continue
                    
                    # Find best buy and sell prices across exchanges
                    exchanges = list(exchange_data.keys())
                    
                    for i, buy_exchange in enumerate(exchanges):
                        for j, sell_exchange in enumerate(exchanges):
                            if i >= j:
                                continue
                            
                            buy_data = exchange_data[buy_exchange]
                            sell_data = exchange_data[sell_exchange]
                            
                            # Check if we can buy low and sell high
                            if sell_data.bid > buy_data.ask:
                                spread = sell_data.bid - buy_data.ask
                                spread_percentage = float(spread / buy_data.ask * 100)
                                
                                # Calculate potential profit (simplified)
                                trade_amount = Decimal("1.0")  # 1 unit
                                transaction_costs = self._calculate_transaction_costs(
                                    buy_exchange, sell_exchange, trade_amount, buy_data.ask, sell_data.bid
                                )
                                
                                potential_profit = spread * trade_amount - transaction_costs
                                
                                if potential_profit > 0 and spread_percentage > 0.1:  # Minimum 0.1% spread
                                    opportunity = ArbitrageOpportunity(
                                        opportunity_id=str(uuid.uuid4()),
                                        symbol=symbol,
                                        buy_exchange=buy_exchange,
                                        sell_exchange=sell_exchange,
                                        buy_price=buy_data.ask,
                                        sell_price=sell_data.bid,
                                        spread=spread,
                                        spread_percentage=spread_percentage,
                                        potential_profit=potential_profit,
                                        confidence=0.8,  # Simplified confidence calculation
                                        valid_until=datetime.now(timezone.utc) + timedelta(minutes=5),
                                        required_capital=buy_data.ask * trade_amount
                                    )
                                    
                                    current_opportunities.append(opportunity)
                
                # Update opportunities list
                self.arbitrage_opportunities = current_opportunities
                self.integration_metrics['arbitrage_opportunities_found'] = len(current_opportunities)
                
                # Emit arbitrage opportunities
                if current_opportunities and self.event_service:
                    await self.event_service.emit_event({
                        'event_type': 'arbitrage.opportunities_detected',
                        'count': len(current_opportunities),
                        'opportunities': [asdict(opp) for opp in current_opportunities[:5]],  # Top 5
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                
            except Exception as e:
                logger.error(f"Error in arbitrage detection loop: {e}")
    
    def _calculate_transaction_costs(self, buy_exchange: str, sell_exchange: str, 
                                   amount: Decimal, buy_price: Decimal, sell_price: Decimal) -> Decimal:
        """Calculate transaction costs for arbitrage trade"""
        buy_config = self.exchange_configs[buy_exchange]
        sell_config = self.exchange_configs[sell_exchange]
        
        buy_fee = buy_price * amount * Decimal(str(buy_config.trading_fees.get('taker', 0.001)))
        sell_fee = sell_price * amount * Decimal(str(sell_config.trading_fees.get('taker', 0.001)))
        
        # Add withdrawal fees (simplified)
        withdrawal_fee = Decimal("0.001") * amount  # Approximate
        
        return buy_fee + sell_fee + withdrawal_fee
    
    async def _balance_synchronization_loop(self):
        """Synchronize balances across exchanges"""
        while True:
            try:
                await asyncio.sleep(60)  # Update every minute
                
                unified_balances = defaultdict(list)
                
                for exchange_id, connector in self.exchanges.items():
                    if connector.status == ExchangeStatus.CONNECTED:
                        try:
                            balances = await connector.get_balances()
                            for balance in balances:
                                unified_balances[balance.currency].append(balance)
                        except Exception as e:
                            logger.error(f"Error getting balances from {exchange_id}: {e}")
                
                self.unified_balances = dict(unified_balances)
                
                # Emit balance update event
                if self.event_service:
                    total_balances = {}
                    for currency, balances in unified_balances.items():
                        total_balances[currency] = {
                            'total': sum(b.total for b in balances),
                            'available': sum(b.available for b in balances),
                            'exchanges': len(balances)
                        }
                    
                    await self.event_service.emit_event({
                        'event_type': 'exchange.balances_updated',
                        'currencies': list(total_balances.keys()),
                        'total_balances': total_balances,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                
            except Exception as e:
                logger.error(f"Error in balance synchronization loop: {e}")
    
    async def _health_monitoring_loop(self):
        """Monitor exchange connection health"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                health_status = {}
                
                for exchange_id, connector in self.exchanges.items():
                    try:
                        # Simple health check - try to get market data
                        market_data = await connector.get_market_data("BTC-USD")
                        if market_data:
                            health_status[exchange_id] = {
                                'status': 'healthy',
                                'last_response': datetime.now(timezone.utc).isoformat(),
                                'latency': 0.1  # Mock latency
                            }
                        else:
                            health_status[exchange_id] = {
                                'status': 'degraded',
                                'last_response': None,
                                'latency': None
                            }
                    except Exception as e:
                        health_status[exchange_id] = {
                            'status': 'error',
                            'error': str(e),
                            'last_response': None,
                            'latency': None
                        }
                
                # Emit health status
                if self.event_service:
                    await self.event_service.emit_event({
                        'event_type': 'exchange.health_status',
                        'exchanges': health_status,
                        'healthy_count': len([s for s in health_status.values() if s['status'] == 'healthy']),
                        'total_count': len(health_status),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
    
    async def _performance_tracking_loop(self):
        """Track integration performance metrics"""
        while True:
            try:
                await asyncio.sleep(300)  # Update every 5 minutes
                
                # Calculate 24h volume across all exchanges
                total_volume = Decimal("0")
                for symbol_data in self.aggregated_market_data.values():
                    for market_data in symbol_data.values():
                        total_volume += market_data.volume_24h
                
                self.integration_metrics['total_volume_24h'] = total_volume
                
                # Emit performance metrics
                if self.event_service:
                    await self.event_service.emit_event({
                        'event_type': 'exchange.performance_metrics',
                        'metrics': self.integration_metrics,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                
            except Exception as e:
                logger.error(f"Error in performance tracking loop: {e}")
    
    # Public API methods
    async def get_best_price(self, symbol: str, side: str) -> Optional[Tuple[str, Decimal]]:
        """Get best price across all exchanges"""
        if symbol not in self.aggregated_market_data:
            return None
        
        exchange_data = self.aggregated_market_data[symbol]
        
        if side == "buy":
            # Find lowest ask price
            best_exchange = min(exchange_data.items(), key=lambda x: x[1].ask)
            return best_exchange[0], best_exchange[1].ask
        else:
            # Find highest bid price
            best_exchange = max(exchange_data.items(), key=lambda x: x[1].bid)
            return best_exchange[0], best_exchange[1].bid
    
    async def execute_arbitrage_trade(self, opportunity: ArbitrageOpportunity) -> Dict[str, Any]:
        """Execute arbitrage trade"""
        try:
            buy_connector = self.exchanges[opportunity.buy_exchange]
            sell_connector = self.exchanges[opportunity.sell_exchange]
            
            # Place buy order
            buy_order_id = await buy_connector.place_order(
                opportunity.symbol, "buy", Decimal("1.0"), opportunity.buy_price, OrderType.LIMIT
            )
            
            # Place sell order
            sell_order_id = await sell_connector.place_order(
                opportunity.symbol, "sell", Decimal("1.0"), opportunity.sell_price, OrderType.LIMIT
            )
            
            # Track the arbitrage trade
            result = {
                "opportunity_id": opportunity.opportunity_id,
                "buy_order_id": buy_order_id,
                "sell_order_id": sell_order_id,
                "status": "pending",
                "potential_profit": float(opportunity.potential_profit),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.arbitrage_history.append(result)
            self.integration_metrics['cross_exchange_orders'] += 2
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing arbitrage trade: {e}")
            raise
    
    async def get_unified_balances(self) -> Dict[str, Dict[str, Any]]:
        """Get unified balances across all exchanges"""
        result = {}
        
        for currency, balances in self.unified_balances.items():
            result[currency] = {
                'total': sum(b.total for b in balances),
                'available': sum(b.available for b in balances),
                'locked': sum(b.locked for b in balances),
                'exchanges': {b.exchange: {'total': float(b.total), 'available': float(b.available)} for b in balances}
            }
        
        return result
    
    async def get_arbitrage_opportunities(self) -> List[ArbitrageOpportunity]:
        """Get current arbitrage opportunities"""
        # Filter out expired opportunities
        current_time = datetime.now(timezone.utc)
        valid_opportunities = [
            opp for opp in self.arbitrage_opportunities
            if opp.valid_until > current_time
        ]
        
        # Sort by potential profit
        valid_opportunities.sort(key=lambda x: x.potential_profit, reverse=True)
        
        return valid_opportunities
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and health metrics"""
        return {
            "service": "multi_exchange_integration",
            "status": "running",
            "connected_exchanges": self.integration_metrics['connected_exchanges'],
            "total_exchanges": len(self.exchange_configs),
            "exchange_status": {
                exchange_id: connector.status.value
                for exchange_id, connector in self.exchanges.items()
            },
            "arbitrage_opportunities": len(self.arbitrage_opportunities),
            "supported_symbols": len(set().union(*[config.supported_symbols for config in self.exchange_configs.values()])),
            "integration_metrics": self.integration_metrics,
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_multi_exchange_integration():
    """Factory function to create MultiExchangeIntegration instance"""
    return MultiExchangeIntegration()