#!/usr/bin/env python3
"""
Risk Management MCP Server
Advanced risk assessment, validation, and compliance monitoring
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
    title="Risk Management MCP Server",
    description="Advanced risk assessment and compliance monitoring",
    version="1.0.0"
)

security = HTTPBearer()

# Enums
class RiskLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    EXTREME = "extreme"

class RiskType(str, Enum):
    MARKET_RISK = "market_risk"
    CREDIT_RISK = "credit_risk"
    LIQUIDITY_RISK = "liquidity_risk"
    OPERATIONAL_RISK = "operational_risk"
    CONCENTRATION_RISK = "concentration_risk"
    COUNTERPARTY_RISK = "counterparty_risk"
    CURRENCY_RISK = "currency_risk"
    REGULATORY_RISK = "regulatory_risk"

class ComplianceRule(str, Enum):
    POSITION_LIMIT = "position_limit"
    SECTOR_LIMIT = "sector_limit"
    SINGLE_STOCK_LIMIT = "single_stock_limit"
    LEVERAGE_LIMIT = "leverage_limit"
    VAR_LIMIT = "var_limit"
    DRAWDOWN_LIMIT = "drawdown_limit"
    CONCENTRATION_LIMIT = "concentration_limit"
    TRADING_HOURS = "trading_hours"
    PROHIBITED_SECURITIES = "prohibited_securities"

class AlertSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# Data models
@dataclass
class RiskLimit:
    rule: ComplianceRule
    limit_type: str  # percentage, absolute, ratio
    limit_value: float
    current_value: float
    threshold_warning: float  # Percentage of limit to trigger warning
    description: str
    is_hard_limit: bool  # If true, blocks trades; if false, just warns
    
@dataclass
class RiskAssessment:
    id: str
    entity_id: str  # Portfolio, order, or position ID
    entity_type: str  # portfolio, order, position
    risk_score: float  # 0-100
    risk_level: RiskLevel
    assessment_time: str
    risks: Dict[RiskType, float]  # Risk type to score mapping
    violations: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    recommendations: List[str]
    var_1day: float
    var_5day: float
    expected_shortfall: float
    correlation_risk: float
    concentration_score: float
    liquidity_score: float

@dataclass
class ComplianceCheck:
    id: str
    rule: ComplianceRule
    entity_id: str
    entity_type: str
    check_time: str
    passed: bool
    current_value: float
    limit_value: float
    violation_severity: AlertSeverity
    message: str
    recommended_action: Optional[str] = None

@dataclass
class RiskAlert:
    id: str
    alert_type: str
    severity: AlertSeverity
    entity_id: str
    entity_type: str
    created_at: str
    message: str
    details: Dict[str, Any]
    acknowledged: bool = False
    resolved: bool = False
    resolution_time: Optional[str] = None

class OrderRiskRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="buy/sell")
    quantity: float = Field(..., description="Order quantity")
    price: Optional[float] = Field(None, description="Order price")
    order_type: str = Field(..., description="Order type")
    portfolio_id: str = Field(..., description="Portfolio ID")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    strategy_id: Optional[str] = Field(None, description="Strategy ID")

class PortfolioRiskRequest(BaseModel):
    portfolio_id: str = Field(..., description="Portfolio ID")
    holdings: Dict[str, Dict] = Field(..., description="Current holdings")
    cash: float = Field(..., description="Cash balance")
    total_value: float = Field(..., description="Total portfolio value")

class RiskLimitRequest(BaseModel):
    rule: ComplianceRule = Field(..., description="Compliance rule")
    limit_type: str = Field(..., description="Limit type")
    limit_value: float = Field(..., description="Limit value")
    threshold_warning: float = Field(0.8, description="Warning threshold (80%)")
    description: str = Field(..., description="Description")
    is_hard_limit: bool = Field(True, description="Is hard limit")

class RiskManagementService:
    def __init__(self):
        self.risk_limits: Dict[str, RiskLimit] = {}
        self.risk_assessments: Dict[str, RiskAssessment] = {}
        self.compliance_checks: Dict[str, List[ComplianceCheck]] = defaultdict(list)
        self.risk_alerts: Dict[str, List[RiskAlert]] = defaultdict(list)
        self.market_data: Dict[str, Dict] = {}
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}
        self.volatility_data: Dict[str, List[float]] = defaultdict(list)
        self.connected_clients: List[WebSocket] = []
        self.monitoring_active = False
        
    async def initialize(self):
        """Initialize the risk management service"""
        # Initialize default risk limits
        await self._setup_default_risk_limits()
        
        # Start monitoring engines
        asyncio.create_task(self._risk_monitor())
        asyncio.create_task(self._compliance_monitor())
        asyncio.create_task(self._market_data_monitor())
        
        # Initialize mock data
        await self._initialize_mock_data()
        
        logger.info("Risk Management Service initialized")

    async def _setup_default_risk_limits(self):
        """Setup default risk limits and compliance rules"""
        default_limits = [
            RiskLimit(
                rule=ComplianceRule.SINGLE_STOCK_LIMIT,
                limit_type="percentage",
                limit_value=10.0,  # 10% max per stock
                current_value=0.0,
                threshold_warning=0.8,
                description="Maximum 10% allocation to any single stock",
                is_hard_limit=True
            ),
            RiskLimit(
                rule=ComplianceRule.SECTOR_LIMIT,
                limit_type="percentage", 
                limit_value=25.0,  # 25% max per sector
                current_value=0.0,
                threshold_warning=0.8,
                description="Maximum 25% allocation to any single sector",
                is_hard_limit=True
            ),
            RiskLimit(
                rule=ComplianceRule.VAR_LIMIT,
                limit_type="percentage",
                limit_value=5.0,  # 5% daily VaR
                current_value=0.0,
                threshold_warning=0.8,
                description="Maximum 5% daily Value at Risk",
                is_hard_limit=True
            ),
            RiskLimit(
                rule=ComplianceRule.LEVERAGE_LIMIT,
                limit_type="ratio",
                limit_value=2.0,  # 2:1 leverage
                current_value=1.0,
                threshold_warning=0.9,
                description="Maximum 2:1 leverage ratio",
                is_hard_limit=True
            ),
            RiskLimit(
                rule=ComplianceRule.DRAWDOWN_LIMIT,
                limit_type="percentage",
                limit_value=15.0,  # 15% max drawdown
                current_value=0.0,
                threshold_warning=0.8,
                description="Maximum 15% drawdown from peak",
                is_hard_limit=False
            ),
            RiskLimit(
                rule=ComplianceRule.CONCENTRATION_LIMIT,
                limit_type="hhi",  # Herfindahl-Hirschman Index
                limit_value=0.3,  # 30% concentration
                current_value=0.0,
                threshold_warning=0.8,
                description="Maximum portfolio concentration (HHI)",
                is_hard_limit=False
            )
        ]
        
        for limit in default_limits:
            self.risk_limits[limit.rule.value] = limit

    async def _initialize_mock_data(self):
        """Initialize with mock market data"""
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'JPM', 'JNJ', 'PG', 'XOM', 'NVDA']
        
        # Market data
        for symbol in symbols:
            self.market_data[symbol] = {
                'price': np.random.uniform(50, 400),
                'volatility': np.random.uniform(0.15, 0.65),
                'beta': np.random.uniform(0.5, 2.0),
                'volume': np.random.uniform(1000000, 10000000),
                'sector': np.random.choice(['Technology', 'Healthcare', 'Finance', 'Energy', 'Consumer']),
                'market_cap': np.random.uniform(10e9, 3000e9),  # $10B to $3T
                'liquidity_score': np.random.uniform(0.3, 1.0),
                'credit_rating': np.random.choice(['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-']),
                'last_update': datetime.now().isoformat()
            }
            
            # Generate volatility history
            self.volatility_data[symbol] = [
                np.random.uniform(0.1, 0.4) for _ in range(252)  # 1 year of data
            ]
        
        # Correlation matrix
        for symbol1 in symbols:
            self.correlation_matrix[symbol1] = {}
            for symbol2 in symbols:
                if symbol1 == symbol2:
                    self.correlation_matrix[symbol1][symbol2] = 1.0
                else:
                    # Technology stocks more correlated with each other
                    if (self.market_data[symbol1]['sector'] == 'Technology' and 
                        self.market_data[symbol2]['sector'] == 'Technology'):
                        corr = np.random.uniform(0.6, 0.9)
                    else:
                        corr = np.random.uniform(0.1, 0.6)
                    self.correlation_matrix[symbol1][symbol2] = corr

    async def _risk_monitor(self):
        """Continuously monitor risk levels"""
        self.monitoring_active = True
        
        while self.monitoring_active:
            try:
                # Monitor all portfolios and positions
                for portfolio_id in ['sample_portfolio_001']:  # Mock portfolio
                    await self._assess_portfolio_risk(portfolio_id)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in risk monitor: {e}")
                await asyncio.sleep(60)

    async def _compliance_monitor(self):
        """Monitor compliance with risk limits"""
        while True:
            try:
                # Check all active limits
                for rule, limit in self.risk_limits.items():
                    await self._check_compliance_rule(limit)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in compliance monitor: {e}")
                await asyncio.sleep(120)

    async def _market_data_monitor(self):
        """Monitor market data for risk factors"""
        while True:
            try:
                # Update market data and recalculate risks
                await self._update_market_risk_factors()
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in market data monitor: {e}")
                await asyncio.sleep(30)

    async def _assess_portfolio_risk(self, portfolio_id: str):
        """Comprehensive portfolio risk assessment"""
        # Mock portfolio data
        portfolio_data = {
            'total_value': 500000.0,
            'cash': 50000.0,
            'holdings': {
                'AAPL': {'quantity': 500, 'value': 150000, 'weight': 0.30},
                'MSFT': {'quantity': 300, 'value': 120000, 'weight': 0.24},
                'GOOGL': {'quantity': 200, 'value': 80000, 'weight': 0.16},
                'TSLA': {'quantity': 400, 'value': 100000, 'weight': 0.20},
                'JPM': {'quantity': 300, 'value': 50000, 'weight': 0.10}
            }
        }
        
        # Calculate risk metrics
        risk_scores = {}
        
        # Market risk
        portfolio_beta = 0
        portfolio_volatility = 0
        total_weight = 0
        
        for symbol, holding in portfolio_data['holdings'].items():
            weight = holding['weight']
            market_data = self.market_data.get(symbol, {})
            
            portfolio_beta += weight * market_data.get('beta', 1.0)
            portfolio_volatility += (weight ** 2) * (market_data.get('volatility', 0.2) ** 2)
            total_weight += weight
        
        portfolio_volatility = np.sqrt(portfolio_volatility)
        risk_scores[RiskType.MARKET_RISK] = min(portfolio_volatility * 100, 100)
        
        # Concentration risk
        weights = [h['weight'] for h in portfolio_data['holdings'].values()]
        hhi = sum(w**2 for w in weights)
        risk_scores[RiskType.CONCENTRATION_RISK] = min(hhi * 100, 100)
        
        # Liquidity risk  
        liquidity_scores = []
        for symbol, holding in portfolio_data['holdings'].items():
            market_data = self.market_data.get(symbol, {})
            liquidity_score = market_data.get('liquidity_score', 0.5)
            liquidity_scores.append(liquidity_score * holding['weight'])
        
        portfolio_liquidity = sum(liquidity_scores)
        risk_scores[RiskType.LIQUIDITY_RISK] = max(0, (1 - portfolio_liquidity) * 100)
        
        # Sector concentration risk
        sector_exposure = defaultdict(float)
        for symbol, holding in portfolio_data['holdings'].items():
            sector = self.market_data.get(symbol, {}).get('sector', 'Unknown')
            sector_exposure[sector] += holding['weight']
        
        max_sector_exposure = max(sector_exposure.values()) if sector_exposure else 0
        risk_scores[RiskType.CONCENTRATION_RISK] += max_sector_exposure * 50
        
        # Calculate VaR
        var_1day = portfolio_volatility * 1.65 * np.sqrt(1/252)  # 95% confidence
        var_5day = portfolio_volatility * 1.65 * np.sqrt(5/252)
        
        # Expected shortfall (CVaR)
        expected_shortfall = var_1day * 1.3  # Approximate
        
        # Overall risk score
        overall_risk_score = np.mean(list(risk_scores.values()))
        
        # Determine risk level
        if overall_risk_score < 20:
            risk_level = RiskLevel.LOW
        elif overall_risk_score < 40:
            risk_level = RiskLevel.MODERATE
        elif overall_risk_score < 60:
            risk_level = RiskLevel.HIGH
        elif overall_risk_score < 80:
            risk_level = RiskLevel.VERY_HIGH
        else:
            risk_level = RiskLevel.EXTREME
        
        # Check for violations
        violations = []
        warnings = []
        recommendations = []
        
        # Check concentration limits
        if max_sector_exposure > 0.25:  # 25% sector limit
            violations.append({
                'rule': 'SECTOR_LIMIT',
                'message': f'Sector exposure {max_sector_exposure:.1%} exceeds 25% limit',
                'severity': 'high'
            })
            recommendations.append('Reduce sector concentration by diversifying holdings')
        
        # Check single stock limits
        for symbol, holding in portfolio_data['holdings'].items():
            if holding['weight'] > 0.10:  # 10% single stock limit
                violations.append({
                    'rule': 'SINGLE_STOCK_LIMIT',
                    'message': f'{symbol} weight {holding["weight"]:.1%} exceeds 10% limit',
                    'severity': 'medium'
                })
                recommendations.append(f'Reduce {symbol} position to below 10%')
        
        # Check VaR limit
        var_percent = var_1day * 100
        if var_percent > 5.0:  # 5% VaR limit
            violations.append({
                'rule': 'VAR_LIMIT',
                'message': f'Daily VaR {var_percent:.2f}% exceeds 5% limit',
                'severity': 'high'
            })
            recommendations.append('Reduce portfolio volatility by adding low-risk assets')
        
        # Create risk assessment
        assessment = RiskAssessment(
            id=str(uuid.uuid4()),
            entity_id=portfolio_id,
            entity_type='portfolio',
            risk_score=overall_risk_score,
            risk_level=risk_level,
            assessment_time=datetime.now().isoformat(),
            risks=risk_scores,
            violations=violations,
            warnings=warnings,
            recommendations=recommendations,
            var_1day=var_1day,
            var_5day=var_5day,
            expected_shortfall=expected_shortfall,
            correlation_risk=hhi,
            concentration_score=hhi,
            liquidity_score=portfolio_liquidity
        )
        
        self.risk_assessments[portfolio_id] = assessment
        
        # Generate alerts for violations
        for violation in violations:
            await self._create_risk_alert(portfolio_id, 'portfolio', violation)
        
        # Notify clients
        await self._notify_risk_assessment(assessment)

    async def _check_compliance_rule(self, limit: RiskLimit):
        """Check compliance with a specific rule"""
        # Mock compliance check
        check_id = str(uuid.uuid4())
        entity_id = "sample_portfolio_001"
        
        # Simulate current values based on rule type
        if limit.rule == ComplianceRule.SINGLE_STOCK_LIMIT:
            limit.current_value = 12.0  # Mock 12% in single stock
        elif limit.rule == ComplianceRule.SECTOR_LIMIT:
            limit.current_value = 30.0  # Mock 30% in tech sector
        elif limit.rule == ComplianceRule.VAR_LIMIT:
            limit.current_value = 6.0  # Mock 6% VaR
        elif limit.rule == ComplianceRule.LEVERAGE_LIMIT:
            limit.current_value = 1.5  # Mock 1.5:1 leverage
        
        # Determine if passed
        passed = limit.current_value <= limit.limit_value
        
        # Determine severity
        if not passed:
            severity = AlertSeverity.HIGH
        elif limit.current_value > (limit.limit_value * limit.threshold_warning):
            severity = AlertSeverity.MEDIUM
        else:
            severity = AlertSeverity.LOW
        
        # Create compliance check
        check = ComplianceCheck(
            id=check_id,
            rule=limit.rule,
            entity_id=entity_id,
            entity_type='portfolio',
            check_time=datetime.now().isoformat(),
            passed=passed,
            current_value=limit.current_value,
            limit_value=limit.limit_value,
            violation_severity=severity,
            message=f'{limit.rule.value}: {limit.current_value:.2f} vs limit {limit.limit_value:.2f}',
            recommended_action=f'Reduce {limit.rule.value} to comply with limit' if not passed else None
        )
        
        self.compliance_checks[entity_id].append(check)
        
        # Keep only last 100 checks per entity
        if len(self.compliance_checks[entity_id]) > 100:
            self.compliance_checks[entity_id] = self.compliance_checks[entity_id][-100:]
        
        # Create alert if violation
        if not passed:
            await self._create_compliance_alert(check)

    async def _update_market_risk_factors(self):
        """Update market risk factors"""
        # Simulate market data updates
        for symbol in self.market_data:
            market_data = self.market_data[symbol]
            
            # Update volatility
            current_vol = market_data['volatility']
            vol_change = np.random.normal(0, 0.01)  # Small random change
            market_data['volatility'] = max(0.05, current_vol + vol_change)
            
            # Update price
            price_change = np.random.normal(0, current_vol * 0.1)
            market_data['price'] *= (1 + price_change)
            
            market_data['last_update'] = datetime.now().isoformat()

    async def assess_order_risk(self, order_request: OrderRiskRequest) -> RiskAssessment:
        """Assess risk for a specific order"""
        symbol = order_request.symbol
        market_data = self.market_data.get(symbol, {})
        
        if not market_data:
            # Unknown symbol - high risk
            risk_score = 80.0
            risk_level = RiskLevel.HIGH
            violations = [{'rule': 'UNKNOWN_SECURITY', 'message': 'Trading unknown security', 'severity': 'high'}]
        else:
            # Calculate order-specific risks
            risk_scores = {}
            
            # Market risk based on volatility
            volatility = market_data.get('volatility', 0.2)
            risk_scores[RiskType.MARKET_RISK] = min(volatility * 100, 100)
            
            # Liquidity risk
            volume = market_data.get('volume', 1000000)
            order_value = order_request.quantity * (order_request.price or market_data['price'])
            liquidity_impact = order_value / (volume * market_data['price'])
            risk_scores[RiskType.LIQUIDITY_RISK] = min(liquidity_impact * 1000, 100)
            
            # Size risk (large orders)
            if order_value > 100000:  # >$100k
                risk_scores[RiskType.OPERATIONAL_RISK] = min((order_value / 100000) * 20, 100)
            else:
                risk_scores[RiskType.OPERATIONAL_RISK] = 10
            
            risk_score = np.mean(list(risk_scores.values()))
            
            # Determine risk level
            if risk_score < 25:
                risk_level = RiskLevel.LOW
            elif risk_score < 50:
                risk_level = RiskLevel.MODERATE
            elif risk_score < 75:
                risk_level = RiskLevel.HIGH
            else:
                risk_level = RiskLevel.VERY_HIGH
            
            violations = []
            
            # Check order-specific limits
            if order_value > 50000:  # $50k order limit
                violations.append({
                    'rule': 'ORDER_SIZE_LIMIT',
                    'message': f'Order size ${order_value:,.0f} exceeds $50k limit',
                    'severity': 'medium'
                })
        
        assessment = RiskAssessment(
            id=str(uuid.uuid4()),
            entity_id=f"order_{order_request.symbol}_{order_request.quantity}",
            entity_type='order',
            risk_score=risk_score,
            risk_level=risk_level,
            assessment_time=datetime.now().isoformat(),
            risks=risk_scores if 'risk_scores' in locals() else {RiskType.MARKET_RISK: risk_score},
            violations=violations,
            warnings=[],
            recommendations=[],
            var_1day=0.0,  # Not applicable for single orders
            var_5day=0.0,
            expected_shortfall=0.0,
            correlation_risk=0.0,
            concentration_score=0.0,
            liquidity_score=market_data.get('liquidity_score', 0.5) if market_data else 0.0
        )
        
        return assessment

    async def _create_risk_alert(self, entity_id: str, entity_type: str, violation: Dict):
        """Create a risk alert"""
        alert = RiskAlert(
            id=str(uuid.uuid4()),
            alert_type='risk_violation',
            severity=AlertSeverity(violation['severity']),
            entity_id=entity_id,
            entity_type=entity_type,
            created_at=datetime.now().isoformat(),
            message=violation['message'],
            details=violation
        )
        
        self.risk_alerts[entity_id].append(alert)
        await self._notify_risk_alert(alert)

    async def _create_compliance_alert(self, check: ComplianceCheck):
        """Create a compliance alert"""
        alert = RiskAlert(
            id=str(uuid.uuid4()),
            alert_type='compliance_violation',
            severity=check.violation_severity,
            entity_id=check.entity_id,
            entity_type=check.entity_type,
            created_at=datetime.now().isoformat(),
            message=f'Compliance violation: {check.message}',
            details=asdict(check)
        )
        
        self.risk_alerts[check.entity_id].append(alert)
        await self._notify_risk_alert(alert)

    async def _notify_risk_assessment(self, assessment: RiskAssessment):
        """Notify clients of risk assessment"""
        message = {
            "type": "risk_assessment",
            "assessment": asdict(assessment),
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(message))
            except:
                self.connected_clients.remove(client)

    async def _notify_risk_alert(self, alert: RiskAlert):
        """Notify clients of risk alert"""
        message = {
            "type": "risk_alert",
            "alert": asdict(alert),
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(message))
            except:
                self.connected_clients.remove(client)

# Initialize service
risk_service = RiskManagementService()

# Authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return credentials.credentials

# API Endpoints
@app.on_event("startup")
async def startup_event():
    await risk_service.initialize()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Risk Management MCP Server", 
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "risk_assessment",
            "compliance_monitoring",
            "trade_validation", 
            "portfolio_risk_analysis"
        ]
    }

@app.get("/metrics")
async def get_metrics():
    return {
        "cpu_usage": 25.8,
        "memory_usage": 35.2,
        "disk_usage": 8.7,
        "network_in": 1024,
        "network_out": 2048,
        "active_connections": len(risk_service.connected_clients),
        "queue_length": 0,
        "errors_last_hour": 0,
        "requests_last_hour": 267,
        "response_time_p95": 23.0
    }

@app.post("/risk/assess/order")
async def assess_order_risk(order_request: OrderRiskRequest, token: str = Depends(get_current_user)):
    try:
        assessment = await risk_service.assess_order_risk(order_request)
        return {"assessment": asdict(assessment), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error assessing order risk: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/risk/assess/portfolio/{portfolio_id}")
async def get_portfolio_risk(portfolio_id: str, token: str = Depends(get_current_user)):
    assessment = risk_service.risk_assessments.get(portfolio_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Portfolio risk assessment not found")
    
    return {"assessment": asdict(assessment), "timestamp": datetime.now().isoformat()}

@app.get("/compliance/limits")
async def get_risk_limits(token: str = Depends(get_current_user)):
    limits = [asdict(limit) for limit in risk_service.risk_limits.values()]
    return {"limits": limits, "total": len(limits), "timestamp": datetime.now().isoformat()}

@app.post("/compliance/limits")
async def create_risk_limit(limit_request: RiskLimitRequest, token: str = Depends(get_current_user)):
    try:
        limit = RiskLimit(
            rule=limit_request.rule,
            limit_type=limit_request.limit_type,
            limit_value=limit_request.limit_value,
            current_value=0.0,
            threshold_warning=limit_request.threshold_warning,
            description=limit_request.description,
            is_hard_limit=limit_request.is_hard_limit
        )
        
        risk_service.risk_limits[limit_request.rule.value] = limit
        
        return {"limit": asdict(limit), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error creating risk limit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/compliance/checks/{entity_id}")
async def get_compliance_checks(entity_id: str, token: str = Depends(get_current_user)):
    checks = risk_service.compliance_checks.get(entity_id, [])
    return {
        "checks": [asdict(check) for check in checks[-50:]],  # Last 50 checks
        "total": len(checks),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/alerts/{entity_id}")
async def get_risk_alerts(entity_id: str, token: str = Depends(get_current_user)):
    alerts = risk_service.risk_alerts.get(entity_id, [])
    return {
        "alerts": [asdict(alert) for alert in alerts[-100:]],  # Last 100 alerts
        "total": len(alerts),
        "timestamp": datetime.now().isoformat()
    }

@app.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, token: str = Depends(get_current_user)):
    # Find and acknowledge alert
    for entity_alerts in risk_service.risk_alerts.values():
        for alert in entity_alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return {"acknowledged": True, "timestamp": datetime.now().isoformat()}
    
    raise HTTPException(status_code=404, detail="Alert not found")

@app.get("/market/risk-factors")
async def get_market_risk_factors(token: str = Depends(get_current_user)):
    return {
        "market_data": risk_service.market_data,
        "correlation_matrix": risk_service.correlation_matrix,
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws/risk/{entity_id}")
async def websocket_endpoint(websocket: WebSocket, entity_id: str):
    await websocket.accept()
    risk_service.connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except:
        pass
    finally:
        if websocket in risk_service.connected_clients:
            risk_service.connected_clients.remove(websocket)

@app.get("/capabilities")
async def get_capabilities():
    return {
        "capabilities": [
            {
                "name": "risk_assessment",
                "description": "Comprehensive risk analysis for orders and portfolios"
            },
            {
                "name": "compliance_monitoring", 
                "description": "Real-time compliance checking against risk limits"
            },
            {
                "name": "trade_validation",
                "description": "Pre-trade risk validation and approval"
            },
            {
                "name": "alert_management",
                "description": "Risk alert generation and management"
            }
        ],
        "risk_types": [rt.value for rt in RiskType],
        "compliance_rules": [cr.value for cr in ComplianceRule],
        "risk_levels": [rl.value for rl in RiskLevel],
        "metrics": [
            "var_95", "var_99", "expected_shortfall", "beta", "volatility",
            "concentration_risk", "liquidity_risk", "correlation_risk"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "risk_management:app", 
        host="0.0.0.0",
        port=8015,
        reload=True,
        log_level="info"
    )