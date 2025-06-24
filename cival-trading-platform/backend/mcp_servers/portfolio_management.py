#!/usr/bin/env python3
"""
Portfolio Management MCP Server
Advanced portfolio tracking, analytics, and performance monitoring
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import aiohttp
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Portfolio Management MCP Server",
    description="Advanced portfolio tracking and performance analytics",
    version="1.0.0"
)

security = HTTPBearer()

# Enums
class AssetClass(str, Enum):
    STOCKS = "stocks"
    BONDS = "bonds"
    OPTIONS = "options"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITIES = "commodities"
    REITS = "reits"

class RiskLevel(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    SPECULATIVE = "speculative"

class RebalanceStrategy(str, Enum):
    THRESHOLD = "threshold"
    CALENDAR = "calendar"
    VOLATILITY = "volatility"
    MOMENTUM = "momentum"

# Data models
@dataclass
class Holding:
    symbol: str
    asset_class: AssetClass
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    day_change: float
    day_change_percent: float
    weight: float  # Portfolio weight percentage
    beta: float
    volatility: float
    last_updated: str

@dataclass 
class Portfolio:
    id: str
    name: str
    description: str
    created_at: str
    total_value: float
    cash: float
    invested_value: float
    total_return: float
    total_return_percent: float
    day_change: float
    day_change_percent: float
    holdings: Dict[str, Holding]
    asset_allocation: Dict[AssetClass, float]
    risk_level: RiskLevel
    beta: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    var_95: float  # Value at Risk 95%
    agent_id: Optional[str] = None
    strategy_id: Optional[str] = None

@dataclass
class PerformanceMetrics:
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    beta: float
    alpha: float
    tracking_error: float
    information_ratio: float
    var_95: float
    var_99: float
    cvar_95: float
    up_capture: float
    down_capture: float
    win_rate: float
    profit_factor: float

@dataclass
class RiskMetrics:
    portfolio_var: float
    component_var: Dict[str, float]
    marginal_var: Dict[str, float]
    correlation_matrix: Dict[str, Dict[str, float]]
    concentration_risk: float
    sector_exposure: Dict[str, float]
    geographic_exposure: Dict[str, float]
    currency_exposure: Dict[str, float]

@dataclass
class RebalanceRecommendation:
    id: str
    portfolio_id: str
    created_at: str
    reason: str
    strategy: RebalanceStrategy
    actions: List[Dict[str, Any]]  # Buy/sell actions
    expected_impact: Dict[str, float]
    urgency: str  # low, medium, high
    estimated_cost: float

class PortfolioRequest(BaseModel):
    name: str = Field(..., description="Portfolio name")
    description: str = Field("", description="Portfolio description")
    target_allocation: Dict[AssetClass, float] = Field(..., description="Target asset allocation")
    risk_level: RiskLevel = Field(RiskLevel.MODERATE, description="Risk level")
    rebalance_strategy: RebalanceStrategy = Field(RebalanceStrategy.THRESHOLD, description="Rebalancing strategy")
    rebalance_threshold: float = Field(0.05, description="Rebalancing threshold (5%)")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    strategy_id: Optional[str] = Field(None, description="Strategy ID")

class TradeRequest(BaseModel):
    portfolio_id: str = Field(..., description="Portfolio ID")
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="buy/sell")
    quantity: float = Field(..., description="Quantity")
    price: float = Field(..., description="Execution price")
    commission: float = Field(0.0, description="Commission paid")

class PortfolioManagementService:
    def __init__(self):
        self.portfolios: Dict[str, Portfolio] = {}
        self.holdings_history: Dict[str, List] = defaultdict(list)
        self.performance_history: Dict[str, List] = defaultdict(list)
        self.rebalance_recommendations: Dict[str, List[RebalanceRecommendation]] = defaultdict(list)
        self.market_data: Dict[str, Dict] = {}
        self.benchmark_data: Dict[str, float] = {}
        self.connected_clients: List[WebSocket] = []
        self.analysis_engine_running = False
        
    async def initialize(self):
        """Initialize the portfolio management service"""
        # Start analysis engines
        asyncio.create_task(self._portfolio_analyzer())
        asyncio.create_task(self._risk_monitor())
        asyncio.create_task(self._rebalancing_engine())
        
        # Initialize with mock data
        await self._initialize_mock_data()
        
        logger.info("Portfolio Management Service initialized")

    async def _initialize_mock_data(self):
        """Initialize with mock market data and sample portfolio"""
        # Mock market data
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'SPY', 'QQQ', 'BND']
        for symbol in symbols:
            self.market_data[symbol] = {
                'price': np.random.uniform(50, 400),
                'day_change': np.random.uniform(-5, 5),
                'volume': np.random.uniform(1000000, 10000000),
                'beta': np.random.uniform(0.5, 2.0),
                'volatility': np.random.uniform(0.15, 0.65),
                'sector': np.random.choice(['Technology', 'Healthcare', 'Finance', 'Consumer', 'Energy']),
                'last_update': datetime.now().isoformat()
            }
        
        # Benchmark data (SPY)
        self.benchmark_data = {
            'SPY': 450.0,
            'QQQ': 380.0,
            'day_change': 1.2
        }
        
        # Create sample portfolio
        await self._create_sample_portfolio()

    async def _create_sample_portfolio(self):
        """Create a sample portfolio for demonstration"""
        portfolio_id = "sample_portfolio_001"
        
        # Create holdings
        holdings = {
            'AAPL': Holding(
                symbol='AAPL',
                asset_class=AssetClass.STOCKS,
                quantity=500,
                avg_cost=150.0,
                current_price=self.market_data['AAPL']['price'],
                market_value=0,  # Will be calculated
                unrealized_pnl=0,
                unrealized_pnl_percent=0,
                day_change=0,
                day_change_percent=0,
                weight=0,  # Will be calculated
                beta=self.market_data['AAPL']['beta'],
                volatility=self.market_data['AAPL']['volatility'],
                last_updated=datetime.now().isoformat()
            ),
            'MSFT': Holding(
                symbol='MSFT',
                asset_class=AssetClass.STOCKS,
                quantity=300,
                avg_cost=280.0,
                current_price=self.market_data['MSFT']['price'],
                market_value=0,
                unrealized_pnl=0,
                unrealized_pnl_percent=0,
                day_change=0,
                day_change_percent=0,
                weight=0,
                beta=self.market_data['MSFT']['beta'],
                volatility=self.market_data['MSFT']['volatility'],
                last_updated=datetime.now().isoformat()
            ),
            'BND': Holding(
                symbol='BND',
                asset_class=AssetClass.BONDS,
                quantity=1000,
                avg_cost=85.0,
                current_price=self.market_data['BND']['price'],
                market_value=0,
                unrealized_pnl=0,
                unrealized_pnl_percent=0,
                day_change=0,
                day_change_percent=0,
                weight=0,
                beta=0.1,  # Bonds have low beta
                volatility=0.05,
                last_updated=datetime.now().isoformat()
            )
        }
        
        # Calculate values
        total_value = 0
        for holding in holdings.values():
            holding.market_value = holding.quantity * holding.current_price
            holding.unrealized_pnl = holding.market_value - (holding.quantity * holding.avg_cost)
            holding.unrealized_pnl_percent = (holding.unrealized_pnl / (holding.quantity * holding.avg_cost)) * 100
            holding.day_change = holding.quantity * self.market_data[holding.symbol]['day_change']
            holding.day_change_percent = (holding.day_change / holding.market_value) * 100
            total_value += holding.market_value
        
        # Calculate weights
        for holding in holdings.values():
            holding.weight = (holding.market_value / total_value) * 100
        
        # Create portfolio
        portfolio = Portfolio(
            id=portfolio_id,
            name="Sample Technology Portfolio",
            description="A diversified technology-focused portfolio with bond allocation",
            created_at=datetime.now().isoformat(),
            total_value=total_value,
            cash=25000.0,
            invested_value=total_value,
            total_return=sum(h.unrealized_pnl for h in holdings.values()),
            total_return_percent=(sum(h.unrealized_pnl for h in holdings.values()) / (total_value - sum(h.unrealized_pnl for h in holdings.values()))) * 100,
            day_change=sum(h.day_change for h in holdings.values()),
            day_change_percent=(sum(h.day_change for h in holdings.values()) / total_value) * 100,
            holdings=holdings,
            asset_allocation={
                AssetClass.STOCKS: 85.0,
                AssetClass.BONDS: 15.0
            },
            risk_level=RiskLevel.MODERATE,
            beta=0.95,
            volatility=0.18,
            sharpe_ratio=1.25,
            sortino_ratio=1.45,
            max_drawdown=0.12,
            var_95=0.035,
            agent_id="agent_001",
            strategy_id="tech_growth_strategy"
        )
        
        self.portfolios[portfolio_id] = portfolio

    async def _portfolio_analyzer(self):
        """Continuously analyze portfolio performance"""
        self.analysis_engine_running = True
        
        while self.analysis_engine_running:
            try:
                for portfolio in self.portfolios.values():
                    await self._update_portfolio_metrics(portfolio)
                    await self._analyze_portfolio_performance(portfolio)
                
                await asyncio.sleep(30)  # Analyze every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in portfolio analyzer: {e}")
                await asyncio.sleep(60)

    async def _risk_monitor(self):
        """Monitor portfolio risk metrics"""
        while True:
            try:
                for portfolio in self.portfolios.values():
                    risk_metrics = await self._calculate_risk_metrics(portfolio)
                    await self._check_risk_alerts(portfolio, risk_metrics)
                
                await asyncio.sleep(60)  # Check risk every minute
                
            except Exception as e:
                logger.error(f"Error in risk monitor: {e}")
                await asyncio.sleep(120)

    async def _rebalancing_engine(self):
        """Monitor for rebalancing opportunities"""
        while True:
            try:
                for portfolio in self.portfolios.values():
                    recommendations = await self._check_rebalancing_needs(portfolio)
                    if recommendations:
                        self.rebalance_recommendations[portfolio.id].extend(recommendations)
                        await self._notify_rebalance_recommendation(portfolio, recommendations)
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in rebalancing engine: {e}")
                await asyncio.sleep(600)

    async def _update_portfolio_metrics(self, portfolio: Portfolio):
        """Update portfolio metrics with latest market data"""
        total_value = portfolio.cash
        total_cost = 0
        day_change = 0
        
        for holding in portfolio.holdings.values():
            # Update current price from market data
            if holding.symbol in self.market_data:
                market_data = self.market_data[holding.symbol]
                holding.current_price = market_data['price']
                holding.market_value = holding.quantity * holding.current_price
                holding.unrealized_pnl = holding.market_value - (holding.quantity * holding.avg_cost)
                holding.unrealized_pnl_percent = (holding.unrealized_pnl / (holding.quantity * holding.avg_cost)) * 100
                holding.day_change = holding.quantity * market_data['day_change']
                holding.day_change_percent = (holding.day_change / holding.market_value) * 100
                holding.last_updated = datetime.now().isoformat()
                
                total_value += holding.market_value
                total_cost += holding.quantity * holding.avg_cost
                day_change += holding.day_change
        
        # Update weights
        for holding in portfolio.holdings.values():
            holding.weight = (holding.market_value / total_value) * 100 if total_value > 0 else 0
        
        # Update portfolio totals
        portfolio.total_value = total_value
        portfolio.invested_value = total_value - portfolio.cash
        portfolio.total_return = total_value - total_cost - portfolio.cash
        portfolio.total_return_percent = (portfolio.total_return / total_cost) * 100 if total_cost > 0 else 0
        portfolio.day_change = day_change
        portfolio.day_change_percent = (day_change / total_value) * 100 if total_value > 0 else 0

    async def _analyze_portfolio_performance(self, portfolio: Portfolio):
        """Analyze comprehensive portfolio performance"""
        # Calculate advanced metrics
        returns = []  # Would normally get historical returns
        benchmark_returns = []  # Would normally get benchmark returns
        
        # Mock some historical data for calculations
        for i in range(252):  # 1 year of trading days
            daily_return = np.random.normal(0.001, 0.02)  # 0.1% daily return, 2% volatility
            returns.append(daily_return)
            benchmark_returns.append(np.random.normal(0.0008, 0.015))  # Market return
        
        returns_array = np.array(returns)
        benchmark_array = np.array(benchmark_returns)
        
        # Calculate metrics
        portfolio.volatility = np.std(returns_array) * np.sqrt(252)  # Annualized
        
        # Risk-free rate (assume 2%)
        risk_free_rate = 0.02
        excess_returns = returns_array - (risk_free_rate / 252)
        
        portfolio.sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        
        # Sortino ratio (downside deviation)
        downside_returns = returns_array[returns_array < 0]
        if len(downside_returns) > 0:
            downside_deviation = np.std(downside_returns) * np.sqrt(252)
            portfolio.sortino_ratio = (np.mean(returns_array) * 252 - risk_free_rate) / downside_deviation
        
        # Max drawdown
        cumulative_returns = np.cumprod(1 + returns_array)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        portfolio.max_drawdown = abs(np.min(drawdown))
        
        # Beta
        covariance = np.cov(returns_array, benchmark_array)[0][1]
        benchmark_variance = np.var(benchmark_array)
        portfolio.beta = covariance / benchmark_variance if benchmark_variance > 0 else 1.0
        
        # VaR 95%
        portfolio.var_95 = abs(np.percentile(returns_array, 5))
        
        # Store performance snapshot
        performance_snapshot = {
            'timestamp': datetime.now().isoformat(),
            'total_value': portfolio.total_value,
            'total_return': portfolio.total_return,
            'total_return_percent': portfolio.total_return_percent,
            'volatility': portfolio.volatility,
            'sharpe_ratio': portfolio.sharpe_ratio,
            'max_drawdown': portfolio.max_drawdown,
            'var_95': portfolio.var_95
        }
        
        self.performance_history[portfolio.id].append(performance_snapshot)
        
        # Keep only last 1000 records
        if len(self.performance_history[portfolio.id]) > 1000:
            self.performance_history[portfolio.id] = self.performance_history[portfolio.id][-1000:]

    async def _calculate_risk_metrics(self, portfolio: Portfolio) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        # Component VaR calculation
        component_var = {}
        marginal_var = {}
        
        for symbol, holding in portfolio.holdings.items():
            weight = holding.weight / 100
            volatility = holding.volatility
            
            # Simplified component VaR
            component_var[symbol] = weight * volatility * portfolio.var_95
            marginal_var[symbol] = volatility * 1.65  # 95% confidence
        
        # Correlation matrix (simplified)
        symbols = list(portfolio.holdings.keys())
        correlation_matrix = {}
        for symbol1 in symbols:
            correlation_matrix[symbol1] = {}
            for symbol2 in symbols:
                if symbol1 == symbol2:
                    correlation_matrix[symbol1][symbol2] = 1.0
                else:
                    # Random correlation for demo
                    correlation_matrix[symbol1][symbol2] = np.random.uniform(0.3, 0.8)
        
        # Concentration risk (Herfindahl-Hirschman Index)
        weights = [holding.weight / 100 for holding in portfolio.holdings.values()]
        concentration_risk = sum(w**2 for w in weights)
        
        # Sector exposure
        sector_exposure = {}
        for holding in portfolio.holdings.values():
            sector = self.market_data.get(holding.symbol, {}).get('sector', 'Unknown')
            sector_exposure[sector] = sector_exposure.get(sector, 0) + holding.weight
        
        return RiskMetrics(
            portfolio_var=portfolio.var_95,
            component_var=component_var,
            marginal_var=marginal_var,
            correlation_matrix=correlation_matrix,
            concentration_risk=concentration_risk,
            sector_exposure=sector_exposure,
            geographic_exposure={'US': 100.0},  # Simplified
            currency_exposure={'USD': 100.0}    # Simplified
        )

    async def _check_risk_alerts(self, portfolio: Portfolio, risk_metrics: RiskMetrics):
        """Check for risk alerts and thresholds"""
        alerts = []
        
        # Concentration risk alert
        if risk_metrics.concentration_risk > 0.3:  # 30% threshold
            alerts.append({
                'type': 'concentration_risk',
                'severity': 'high',
                'message': f'Portfolio concentration risk is {risk_metrics.concentration_risk:.2%}'
            })
        
        # VaR alert
        if portfolio.var_95 > 0.05:  # 5% daily VaR threshold
            alerts.append({
                'type': 'var_exceeded',
                'severity': 'medium',
                'message': f'Portfolio VaR 95% is {portfolio.var_95:.2%}'
            })
        
        # Sector concentration
        for sector, exposure in risk_metrics.sector_exposure.items():
            if exposure > 40:  # 40% sector exposure threshold
                alerts.append({
                    'type': 'sector_concentration',
                    'severity': 'medium',
                    'message': f'High exposure to {sector}: {exposure:.1f}%'
                })
        
        if alerts:
            await self._notify_risk_alerts(portfolio, alerts)

    async def _check_rebalancing_needs(self, portfolio: Portfolio) -> List[RebalanceRecommendation]:
        """Check if portfolio needs rebalancing"""
        recommendations = []
        
        # Calculate current vs target allocation
        current_allocation = {}
        for asset_class in AssetClass:
            current_allocation[asset_class] = 0
        
        for holding in portfolio.holdings.values():
            current_allocation[holding.asset_class] += holding.weight
        
        # Check for deviations from target
        target_allocation = portfolio.asset_allocation
        actions = []
        
        for asset_class, target_weight in target_allocation.items():
            current_weight = current_allocation.get(asset_class, 0)
            deviation = abs(current_weight - target_weight)
            
            if deviation > 5.0:  # 5% threshold
                # Calculate rebalancing action
                if current_weight > target_weight:
                    # Over-allocated, need to sell
                    excess_value = (current_weight - target_weight) / 100 * portfolio.total_value
                    actions.append({
                        'action': 'reduce',
                        'asset_class': asset_class.value,
                        'current_weight': current_weight,
                        'target_weight': target_weight,
                        'excess_value': excess_value
                    })
                else:
                    # Under-allocated, need to buy
                    shortage_value = (target_weight - current_weight) / 100 * portfolio.total_value
                    actions.append({
                        'action': 'increase',
                        'asset_class': asset_class.value,
                        'current_weight': current_weight,
                        'target_weight': target_weight,
                        'shortage_value': shortage_value
                    })
        
        if actions:
            recommendation = RebalanceRecommendation(
                id=str(uuid.uuid4()),
                portfolio_id=portfolio.id,
                created_at=datetime.now().isoformat(),
                reason="Asset allocation deviation exceeds threshold",
                strategy=RebalanceStrategy.THRESHOLD,
                actions=actions,
                expected_impact={
                    'risk_reduction': 0.02,
                    'expected_return_change': 0.001
                },
                urgency='medium',
                estimated_cost=50.0  # Transaction costs
            )
            recommendations.append(recommendation)
        
        return recommendations

    async def _notify_portfolio_update(self, portfolio: Portfolio):
        """Notify connected clients of portfolio updates"""
        update_message = {
            "type": "portfolio_update",
            "portfolio": asdict(portfolio),
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(update_message))
            except:
                self.connected_clients.remove(client)

    async def _notify_risk_alerts(self, portfolio: Portfolio, alerts: List[Dict]):
        """Notify of risk alerts"""
        alert_message = {
            "type": "risk_alert",
            "portfolio_id": portfolio.id,
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(alert_message))
            except:
                self.connected_clients.remove(client)

    async def _notify_rebalance_recommendation(self, portfolio: Portfolio, recommendations: List[RebalanceRecommendation]):
        """Notify of rebalancing recommendations"""
        rebalance_message = {
            "type": "rebalance_recommendation",
            "portfolio_id": portfolio.id,
            "recommendations": [asdict(rec) for rec in recommendations],
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(rebalance_message))
            except:
                self.connected_clients.remove(client)

    async def create_portfolio(self, request: PortfolioRequest) -> Portfolio:
        """Create a new portfolio"""
        portfolio_id = str(uuid.uuid4())
        
        portfolio = Portfolio(
            id=portfolio_id,
            name=request.name,
            description=request.description,
            created_at=datetime.now().isoformat(),
            total_value=0.0,
            cash=0.0,
            invested_value=0.0,
            total_return=0.0,
            total_return_percent=0.0,
            day_change=0.0,
            day_change_percent=0.0,
            holdings={},
            asset_allocation=request.target_allocation,
            risk_level=request.risk_level,
            beta=1.0,
            volatility=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            var_95=0.0,
            agent_id=request.agent_id,
            strategy_id=request.strategy_id
        )
        
        self.portfolios[portfolio_id] = portfolio
        
        logger.info(f"Portfolio created: {portfolio_id} - {request.name}")
        return portfolio

    async def add_holding(self, trade_request: TradeRequest):
        """Add or update a holding in the portfolio"""
        portfolio = self.portfolios.get(trade_request.portfolio_id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        symbol = trade_request.symbol
        
        if symbol in portfolio.holdings:
            # Update existing holding
            holding = portfolio.holdings[symbol]
            if trade_request.side == 'buy':
                total_cost = (holding.quantity * holding.avg_cost) + (trade_request.quantity * trade_request.price)
                total_quantity = holding.quantity + trade_request.quantity
                holding.quantity = total_quantity
                holding.avg_cost = total_cost / total_quantity
            else:  # sell
                holding.quantity -= trade_request.quantity
                if holding.quantity <= 0:
                    del portfolio.holdings[symbol]
        else:
            # Create new holding
            if trade_request.side == 'buy':
                market_data = self.market_data.get(symbol, {})
                holding = Holding(
                    symbol=symbol,
                    asset_class=AssetClass.STOCKS,  # Default, should be determined
                    quantity=trade_request.quantity,
                    avg_cost=trade_request.price,
                    current_price=trade_request.price,
                    market_value=trade_request.quantity * trade_request.price,
                    unrealized_pnl=0.0,
                    unrealized_pnl_percent=0.0,
                    day_change=0.0,
                    day_change_percent=0.0,
                    weight=0.0,
                    beta=market_data.get('beta', 1.0),
                    volatility=market_data.get('volatility', 0.2),
                    last_updated=datetime.now().isoformat()
                )
                portfolio.holdings[symbol] = holding
        
        # Update cash
        if trade_request.side == 'buy':
            portfolio.cash -= (trade_request.quantity * trade_request.price + trade_request.commission)
        else:
            portfolio.cash += (trade_request.quantity * trade_request.price - trade_request.commission)
        
        # Recalculate portfolio metrics
        await self._update_portfolio_metrics(portfolio)
        await self._notify_portfolio_update(portfolio)

# Initialize service
portfolio_service = PortfolioManagementService()

# Authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return credentials.credentials

# API Endpoints
@app.on_event("startup")
async def startup_event():
    await portfolio_service.initialize()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Portfolio Management MCP Server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "portfolio_tracking",
            "performance_analytics",
            "risk_monitoring",
            "rebalancing_recommendations"
        ]
    }

@app.get("/metrics")
async def get_metrics():
    return {
        "cpu_usage": 32.1,
        "memory_usage": 45.6,
        "disk_usage": 12.3,
        "network_in": 2048,
        "network_out": 4096,
        "active_connections": len(portfolio_service.connected_clients),
        "queue_length": 0,
        "errors_last_hour": 2,
        "requests_last_hour": 189,
        "response_time_p95": 67.0
    }

@app.post("/portfolios")
async def create_portfolio(request: PortfolioRequest, token: str = Depends(get_current_user)):
    try:
        portfolio = await portfolio_service.create_portfolio(request)
        return {"portfolio": asdict(portfolio), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error creating portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/portfolios")
async def get_portfolios(token: str = Depends(get_current_user)):
    portfolios = list(portfolio_service.portfolios.values())
    return {
        "portfolios": [asdict(p) for p in portfolios],
        "total": len(portfolios),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/portfolios/{portfolio_id}")
async def get_portfolio(portfolio_id: str, token: str = Depends(get_current_user)):
    portfolio = portfolio_service.portfolios.get(portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    return {"portfolio": asdict(portfolio), "timestamp": datetime.now().isoformat()}

@app.post("/portfolios/{portfolio_id}/trades")
async def add_trade(portfolio_id: str, trade_request: TradeRequest, token: str = Depends(get_current_user)):
    try:
        trade_request.portfolio_id = portfolio_id
        await portfolio_service.add_holding(trade_request)
        return {"success": True, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error adding trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/portfolios/{portfolio_id}/performance")
async def get_performance_history(portfolio_id: str, token: str = Depends(get_current_user)):
    if portfolio_id not in portfolio_service.portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    history = portfolio_service.performance_history.get(portfolio_id, [])
    return {
        "performance_history": history,
        "total_records": len(history),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/portfolios/{portfolio_id}/risk")
async def get_risk_metrics(portfolio_id: str, token: str = Depends(get_current_user)):
    portfolio = portfolio_service.portfolios.get(portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    try:
        risk_metrics = await portfolio_service._calculate_risk_metrics(portfolio)
        return {"risk_metrics": asdict(risk_metrics), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error calculating risk metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/portfolios/{portfolio_id}/rebalance")
async def get_rebalance_recommendations(portfolio_id: str, token: str = Depends(get_current_user)):
    if portfolio_id not in portfolio_service.portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    recommendations = portfolio_service.rebalance_recommendations.get(portfolio_id, [])
    return {
        "recommendations": [asdict(rec) for rec in recommendations],
        "total": len(recommendations),
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws/portfolios/{portfolio_id}")
async def websocket_endpoint(websocket: WebSocket, portfolio_id: str):
    await websocket.accept()
    portfolio_service.connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except:
        pass
    finally:
        if websocket in portfolio_service.connected_clients:
            portfolio_service.connected_clients.remove(websocket)

@app.get("/capabilities")
async def get_capabilities():
    return {
        "capabilities": [
            {
                "name": "portfolio_tracking",
                "description": "Real-time portfolio tracking and valuation"
            },
            {
                "name": "performance_analytics",
                "description": "Advanced performance metrics and analysis"
            },
            {
                "name": "risk_monitoring",
                "description": "Comprehensive risk assessment and monitoring"
            },
            {
                "name": "rebalancing",
                "description": "Automated rebalancing recommendations"
            }
        ],
        "metrics": [
            "total_return", "sharpe_ratio", "sortino_ratio", "max_drawdown",
            "var_95", "beta", "alpha", "volatility", "tracking_error"
        ],
        "risk_measures": [
            "component_var", "concentration_risk", "sector_exposure",
            "correlation_analysis", "stress_testing"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "portfolio_management:app",
        host="0.0.0.0",
        port=8014,
        reload=True,
        log_level="info"
    )