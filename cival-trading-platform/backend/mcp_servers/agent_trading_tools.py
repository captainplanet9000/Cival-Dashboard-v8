#!/usr/bin/env python3
"""
Agent Trading Tools MCP Server
Specialized tools for autonomous trading agents with LLM integration
Optimized for Google Gemini tool calling
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from decimal import Decimal
import aiohttp
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Agent Trading Tools MCP Server",
    description="Advanced trading tools for autonomous agents with LLM integration",
    version="2.0.0"
)

security = HTTPBearer()

# Tool definitions for LLM integration
class ToolType(str, Enum):
    MARKET_ANALYSIS = "market_analysis"
    TRADE_EXECUTION = "trade_execution"
    PORTFOLIO_MANAGEMENT = "portfolio_management"
    RISK_ASSESSMENT = "risk_assessment"
    PERFORMANCE_TRACKING = "performance_tracking"
    MARKET_SCANNING = "market_scanning"

@dataclass
class ToolResult:
    """Standard tool result format"""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    tool_name: str = ""
    execution_time_ms: float = 0.0
    timestamp: str = ""

class AgentTradingTools:
    """
    Advanced trading tools optimized for agent use with LLM tool calling
    """
    
    def __init__(self):
        self.tools_registry = {}
        self.execution_history = []
        self.performance_metrics = {}
        self._register_tools()
        logger.info("AgentTradingTools initialized with enhanced LLM integration")
    
    def _register_tools(self):
        """Register all available tools"""
        self.tools_registry = {
            # Market Analysis Tools
            "get_market_sentiment": {
                "type": ToolType.MARKET_ANALYSIS,
                "description": "Analyze market sentiment for a specific symbol",
                "parameters": {
                    "symbol": "string",
                    "timeframe": "string (1h, 4h, 1d)",
                    "sources": "list of strings (news, social, technical)"
                },
                "function": self.get_market_sentiment
            },
            "analyze_price_action": {
                "type": ToolType.MARKET_ANALYSIS,
                "description": "Detailed price action analysis with technical indicators",
                "parameters": {
                    "symbol": "string",
                    "timeframe": "string",
                    "indicators": "list of strings"
                },
                "function": self.analyze_price_action
            },
            "scan_arbitrage_opportunities": {
                "type": ToolType.MARKET_SCANNING,
                "description": "Scan for arbitrage opportunities across exchanges",
                "parameters": {
                    "symbols": "list of strings",
                    "min_spread": "float",
                    "exchanges": "list of strings"
                },
                "function": self.scan_arbitrage_opportunities
            },
            
            # Trading Execution Tools
            "execute_smart_order": {
                "type": ToolType.TRADE_EXECUTION,
                "description": "Execute orders with advanced strategies (TWAP, VWAP, Iceberg)",
                "parameters": {
                    "symbol": "string",
                    "side": "string (buy/sell)",
                    "quantity": "float",
                    "strategy": "string (market, limit, twap, vwap, iceberg)",
                    "price": "float (optional)",
                    "time_window": "int (minutes)"
                },
                "function": self.execute_smart_order
            },
            "get_order_book_depth": {
                "type": ToolType.MARKET_ANALYSIS,
                "description": "Get detailed order book analysis",
                "parameters": {
                    "symbol": "string",
                    "depth": "int (number of levels)"
                },
                "function": self.get_order_book_depth
            },
            
            # Portfolio Management Tools
            "get_portfolio_positions": {
                "type": ToolType.PORTFOLIO_MANAGEMENT,
                "description": "Get current portfolio positions with real-time P&L",
                "parameters": {
                    "include_closed": "bool",
                    "filter_by_symbol": "string (optional)"
                },
                "function": self.get_portfolio_positions
            },
            "calculate_optimal_position_size": {
                "type": ToolType.RISK_ASSESSMENT,
                "description": "Calculate optimal position size using Kelly Criterion and risk management",
                "parameters": {
                    "symbol": "string",
                    "strategy": "string",
                    "win_rate": "float",
                    "avg_win": "float",
                    "avg_loss": "float",
                    "max_risk": "float"
                },
                "function": self.calculate_optimal_position_size
            },
            
            # Risk Assessment Tools
            "calculate_portfolio_var": {
                "type": ToolType.RISK_ASSESSMENT,
                "description": "Calculate portfolio Value at Risk with Monte Carlo simulation",
                "parameters": {
                    "confidence_level": "float (0.95, 0.99)",
                    "time_horizon": "int (days)",
                    "simulation_runs": "int"
                },
                "function": self.calculate_portfolio_var
            },
            "stress_test_portfolio": {
                "type": ToolType.RISK_ASSESSMENT,
                "description": "Run stress tests on portfolio under various scenarios",
                "parameters": {
                    "scenario": "string (market_crash, volatility_spike, interest_rate_change)",
                    "severity": "float (0.1 to 1.0)"
                },
                "function": self.stress_test_portfolio
            },
            
            # Performance Tracking Tools
            "get_agent_performance": {
                "type": ToolType.PERFORMANCE_TRACKING,
                "description": "Get comprehensive agent performance metrics",
                "parameters": {
                    "agent_id": "string",
                    "period": "string (1d, 1w, 1m, 3m, 1y)",
                    "metrics": "list of strings"
                },
                "function": self.get_agent_performance
            },
            "compare_strategy_performance": {
                "type": ToolType.PERFORMANCE_TRACKING,
                "description": "Compare performance of different trading strategies",
                "parameters": {
                    "strategies": "list of strings",
                    "period": "string",
                    "benchmark": "string"
                },
                "function": self.compare_strategy_performance
            }
        }
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """Execute a tool with given parameters"""
        start_time = datetime.now(timezone.utc)
        
        try:
            if tool_name not in self.tools_registry:
                return ToolResult(
                    success=False,
                    data={},
                    error=f"Tool '{tool_name}' not found",
                    tool_name=tool_name,
                    timestamp=start_time.isoformat()
                )
            
            tool_config = self.tools_registry[tool_name]
            tool_function = tool_config["function"]
            
            # Execute tool function
            result_data = await tool_function(**parameters)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            result = ToolResult(
                success=True,
                data=result_data,
                tool_name=tool_name,
                execution_time_ms=execution_time,
                timestamp=start_time.isoformat()
            )
            
            # Track execution
            self.execution_history.append(asdict(result))
            
            logger.info(f"Tool '{tool_name}' executed successfully in {execution_time:.2f}ms")
            return result
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            result = ToolResult(
                success=False,
                data={},
                error=str(e),
                tool_name=tool_name,
                execution_time_ms=execution_time,
                timestamp=start_time.isoformat()
            )
            
            logger.error(f"Tool '{tool_name}' failed: {e}")
            return result
    
    # Market Analysis Tools Implementation
    async def get_market_sentiment(self, symbol: str, timeframe: str = "1d", sources: List[str] = None) -> Dict[str, Any]:
        """Analyze market sentiment for a symbol"""
        if sources is None:
            sources = ["news", "social", "technical"]
        
        # Mock sentiment analysis - in production, this would integrate with real sentiment APIs
        sentiment_data = {
            "symbol": symbol,
            "timeframe": timeframe,
            "overall_sentiment": "bullish",
            "sentiment_score": 0.72,  # -1 to 1 scale
            "confidence": 0.85,
            "sources_analyzed": sources,
            "breakdown": {
                "news_sentiment": 0.68,
                "social_sentiment": 0.75,
                "technical_sentiment": 0.73
            },
            "key_factors": [
                "Positive earnings reports",
                "Strong technical breakout",
                "Increased institutional buying"
            ],
            "risk_factors": [
                "Market volatility",
                "Sector rotation concerns"
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return sentiment_data
    
    async def analyze_price_action(self, symbol: str, timeframe: str = "1h", indicators: List[str] = None) -> Dict[str, Any]:
        """Detailed price action analysis"""
        if indicators is None:
            indicators = ["rsi", "macd", "bollinger_bands", "moving_averages"]
        
        # Mock technical analysis - in production, this would calculate real indicators
        analysis = {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": 45234.56,
            "price_change_24h": 2.34,
            "volume_24h": 1250000,
            "technical_indicators": {
                "rsi": {
                    "value": 68.5,
                    "signal": "neutral",
                    "description": "RSI approaching overbought territory"
                },
                "macd": {
                    "macd_line": 245.67,
                    "signal_line": 234.12,
                    "histogram": 11.55,
                    "signal": "bullish",
                    "description": "MACD above signal line, bullish momentum"
                },
                "bollinger_bands": {
                    "upper_band": 46500,
                    "middle_band": 45000,
                    "lower_band": 43500,
                    "position": "upper_half",
                    "signal": "neutral"
                },
                "moving_averages": {
                    "sma_20": 44890,
                    "sma_50": 44200,
                    "ema_12": 45100,
                    "ema_26": 44750,
                    "trend": "bullish"
                }
            },
            "support_resistance": {
                "resistance_levels": [46000, 47500, 49000],
                "support_levels": [44000, 42500, 41000]
            },
            "pattern_recognition": {
                "current_pattern": "ascending_triangle",
                "confidence": 0.78,
                "target_price": 48000,
                "breakout_probability": 0.65
            },
            "recommendation": {
                "action": "buy",
                "confidence": 0.75,
                "reasoning": "Strong technical setup with bullish momentum indicators",
                "entry_price": 45200,
                "stop_loss": 43800,
                "take_profit": 47500
            }
        }
        
        return analysis
    
    async def scan_arbitrage_opportunities(self, symbols: List[str], min_spread: float = 0.001, exchanges: List[str] = None) -> Dict[str, Any]:
        """Scan for arbitrage opportunities"""
        if exchanges is None:
            exchanges = ["binance", "coinbase", "kraken"]
        
        # Mock arbitrage scanning - in production, this would check real exchange prices
        opportunities = []
        
        for symbol in symbols:
            # Simulate price differences across exchanges
            base_price = 45000  # Mock base price
            exchange_prices = {
                "binance": base_price * (1 + 0.002),
                "coinbase": base_price * (1 - 0.001),
                "kraken": base_price * (1 + 0.0015)
            }
            
            # Find arbitrage opportunities
            for buy_exchange in exchanges:
                for sell_exchange in exchanges:
                    if buy_exchange == sell_exchange:
                        continue
                    
                    buy_price = exchange_prices[buy_exchange]
                    sell_price = exchange_prices[sell_exchange]
                    spread = (sell_price - buy_price) / buy_price
                    
                    if spread > min_spread:
                        opportunities.append({
                            "symbol": symbol,
                            "buy_exchange": buy_exchange,
                            "sell_exchange": sell_exchange,
                            "buy_price": buy_price,
                            "sell_price": sell_price,
                            "spread_percentage": spread * 100,
                            "potential_profit": spread,
                            "estimated_volume": 1000,
                            "execution_risk": "low",
                            "time_to_execute": 30  # seconds
                        })
        
        return {
            "opportunities_found": len(opportunities),
            "opportunities": opportunities[:10],  # Top 10 opportunities
            "scan_parameters": {
                "symbols": symbols,
                "min_spread": min_spread,
                "exchanges": exchanges
            },
            "market_conditions": {
                "volatility": "moderate",
                "liquidity": "high",
                "spread_environment": "favorable"
            }
        }
    
    # Trading Execution Tools Implementation
    async def execute_smart_order(self, symbol: str, side: str, quantity: float, strategy: str, price: float = None, time_window: int = 60) -> Dict[str, Any]:
        """Execute smart orders with advanced strategies"""
        order_id = str(uuid.uuid4())
        
        # Simulate smart order execution
        execution_result = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "strategy": strategy,
            "status": "executed",
            "execution_details": {
                "avg_fill_price": price if price else 45234.56,
                "total_fills": 5 if strategy in ["twap", "vwap", "iceberg"] else 1,
                "execution_time_seconds": 45 if strategy in ["twap", "vwap"] else 2,
                "slippage": 0.02,  # 2 basis points
                "market_impact": 0.01  # 1 basis point
            },
            "fees": {
                "commission": quantity * 0.001,  # 0.1% commission
                "exchange_fees": quantity * 0.0005
            },
            "performance_metrics": {
                "vwap_performance": 0.005 if strategy == "vwap" else None,
                "implementation_shortfall": 0.003,
                "timing_risk": "low"
            }
        }
        
        return execution_result
    
    async def get_order_book_depth(self, symbol: str, depth: int = 10) -> Dict[str, Any]:
        """Get detailed order book analysis"""
        # Mock order book data - in production, this would fetch real order book
        bids = []
        asks = []
        
        base_price = 45234.56
        
        # Generate mock bids (buy orders)
        for i in range(depth):
            bid_price = base_price - (i + 1) * 10
            bid_size = 100 + i * 50
            bids.append([bid_price, bid_size])
        
        # Generate mock asks (sell orders)
        for i in range(depth):
            ask_price = base_price + (i + 1) * 10
            ask_size = 100 + i * 50
            asks.append([ask_price, ask_size])
        
        # Calculate order book metrics
        total_bid_volume = sum([bid[1] for bid in bids])
        total_ask_volume = sum([ask[1] for ask in asks])
        spread = asks[0][0] - bids[0][0]
        mid_price = (asks[0][0] + bids[0][0]) / 2
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "bids": bids,
            "asks": asks,
            "metrics": {
                "spread": spread,
                "spread_percentage": (spread / mid_price) * 100,
                "mid_price": mid_price,
                "total_bid_volume": total_bid_volume,
                "total_ask_volume": total_ask_volume,
                "bid_ask_ratio": total_bid_volume / total_ask_volume,
                "liquidity_score": 8.5,  # 1-10 scale
                "market_depth_score": 7.8
            },
            "analysis": {
                "market_sentiment": "slightly_bullish" if total_bid_volume > total_ask_volume else "neutral",
                "liquidity_assessment": "high",
                "optimal_order_size": min(total_bid_volume, total_ask_volume) * 0.1
            }
        }
    
    # Portfolio Management Tools Implementation
    async def get_portfolio_positions(self, include_closed: bool = False, filter_by_symbol: str = None) -> Dict[str, Any]:
        """Get portfolio positions with real-time P&L"""
        # Mock portfolio data
        positions = [
            {
                "symbol": "BTCUSD",
                "side": "long",
                "quantity": 0.5,
                "entry_price": 44250.00,
                "current_price": 45234.56,
                "unrealized_pnl": 492.28,
                "unrealized_pnl_percentage": 2.23,
                "market_value": 22617.28,
                "cost_basis": 22125.00,
                "position_age_hours": 36,
                "stop_loss": 42800.00,
                "take_profit": 47500.00
            },
            {
                "symbol": "ETHUSD",
                "side": "long",
                "quantity": 5.0,
                "entry_price": 2234.50,
                "current_price": 2289.75,
                "unrealized_pnl": 276.25,
                "unrealized_pnl_percentage": 2.47,
                "market_value": 11448.75,
                "cost_basis": 11172.50,
                "position_age_hours": 18,
                "stop_loss": 2100.00,
                "take_profit": 2450.00
            }
        ]
        
        # Filter by symbol if specified
        if filter_by_symbol:
            positions = [pos for pos in positions if pos["symbol"] == filter_by_symbol]
        
        # Calculate portfolio totals
        total_market_value = sum([pos["market_value"] for pos in positions])
        total_unrealized_pnl = sum([pos["unrealized_pnl"] for pos in positions])
        total_cost_basis = sum([pos["cost_basis"] for pos in positions])
        
        return {
            "positions": positions,
            "summary": {
                "total_positions": len(positions),
                "total_market_value": total_market_value,
                "total_cost_basis": total_cost_basis,
                "total_unrealized_pnl": total_unrealized_pnl,
                "total_unrealized_pnl_percentage": (total_unrealized_pnl / total_cost_basis) * 100 if total_cost_basis > 0 else 0,
                "portfolio_beta": 1.15,
                "portfolio_volatility": 0.28,
                "sharpe_ratio": 1.85
            },
            "risk_metrics": {
                "portfolio_var_95": total_market_value * 0.02,  # 2% VaR
                "max_drawdown": 0.08,
                "correlation_risk": 0.65
            }
        }
    
    async def calculate_optimal_position_size(self, symbol: str, strategy: str, win_rate: float, avg_win: float, avg_loss: float, max_risk: float) -> Dict[str, Any]:
        """Calculate optimal position size using Kelly Criterion"""
        # Kelly Criterion calculation
        kelly_percentage = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        
        # Apply safety factor
        safety_factor = 0.25  # Use 25% of Kelly recommendation
        recommended_percentage = kelly_percentage * safety_factor
        
        # Cap at max risk
        final_percentage = min(recommended_percentage, max_risk)
        
        # Get current portfolio value (mock)
        portfolio_value = 100000  # $100k portfolio
        
        position_value = portfolio_value * final_percentage
        
        return {
            "symbol": symbol,
            "strategy": strategy,
            "kelly_percentage": kelly_percentage,
            "recommended_percentage": final_percentage,
            "position_value": position_value,
            "calculation_details": {
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "expected_value": win_rate * avg_win - (1 - win_rate) * avg_loss,
                "safety_factor": safety_factor,
                "max_risk_limit": max_risk
            },
            "risk_assessment": {
                "risk_level": "low" if final_percentage < 0.02 else "medium" if final_percentage < 0.05 else "high",
                "max_loss_potential": position_value * avg_loss,
                "expected_profit": position_value * (win_rate * avg_win - (1 - win_rate) * avg_loss)
            }
        }
    
    # Risk Assessment Tools Implementation
    async def calculate_portfolio_var(self, confidence_level: float = 0.95, time_horizon: int = 1, simulation_runs: int = 10000) -> Dict[str, Any]:
        """Calculate portfolio VaR with Monte Carlo simulation"""
        # Mock VaR calculation - in production, this would run actual Monte Carlo simulation
        portfolio_value = 100000
        
        # Simulate portfolio returns
        daily_volatility = 0.02  # 2% daily volatility
        
        # Calculate VaR
        z_score = 1.645 if confidence_level == 0.95 else 2.326  # 95% or 99%
        var_amount = portfolio_value * daily_volatility * z_score * (time_horizon ** 0.5)
        
        # Expected Shortfall (Conditional VaR)
        expected_shortfall = var_amount * 1.3  # Typically 30% higher than VaR
        
        return {
            "confidence_level": confidence_level,
            "time_horizon_days": time_horizon,
            "portfolio_value": portfolio_value,
            "var_amount": var_amount,
            "var_percentage": (var_amount / portfolio_value) * 100,
            "expected_shortfall": expected_shortfall,
            "es_percentage": (expected_shortfall / portfolio_value) * 100,
            "simulation_details": {
                "runs": simulation_runs,
                "daily_volatility": daily_volatility,
                "worst_case_scenario": var_amount * 2,
                "best_case_scenario": var_amount * -0.5
            },
            "risk_assessment": {
                "risk_level": "low" if var_amount < portfolio_value * 0.02 else "medium" if var_amount < portfolio_value * 0.05 else "high",
                "recommendation": "Acceptable risk level" if var_amount < portfolio_value * 0.03 else "Consider reducing exposure"
            }
        }
    
    async def stress_test_portfolio(self, scenario: str, severity: float = 0.5) -> Dict[str, Any]:
        """Run stress tests on portfolio"""
        portfolio_value = 100000
        
        # Define stress scenarios
        scenarios = {
            "market_crash": {
                "description": "Market-wide selloff",
                "impact_factors": {
                    "equity_impact": -0.20 * severity,
                    "crypto_impact": -0.35 * severity,
                    "bond_impact": -0.05 * severity,
                    "correlation_increase": 0.9
                }
            },
            "volatility_spike": {
                "description": "Sudden volatility increase",
                "impact_factors": {
                    "volatility_multiplier": 2.0 + severity,
                    "spread_widening": 0.5 * severity,
                    "liquidity_reduction": 0.3 * severity
                }
            },
            "interest_rate_change": {
                "description": "Interest rate shock",
                "impact_factors": {
                    "rate_change_bps": 200 * severity,
                    "bond_duration_impact": -0.06 * severity,
                    "equity_multiple_compression": -0.1 * severity
                }
            }
        }
        
        scenario_config = scenarios.get(scenario, scenarios["market_crash"])
        
        # Calculate portfolio impact
        estimated_loss = portfolio_value * abs(min(scenario_config["impact_factors"].values()))
        portfolio_after_stress = portfolio_value - estimated_loss
        
        return {
            "scenario": scenario,
            "severity": severity,
            "description": scenario_config["description"],
            "portfolio_before": portfolio_value,
            "estimated_loss": estimated_loss,
            "portfolio_after": portfolio_after_stress,
            "loss_percentage": (estimated_loss / portfolio_value) * 100,
            "impact_factors": scenario_config["impact_factors"],
            "recovery_analysis": {
                "estimated_recovery_time_days": 45 + (severity * 30),
                "recovery_probability": 0.85 - (severity * 0.2),
                "mitigation_strategies": [
                    "Increase cash allocation",
                    "Add hedging positions",
                    "Reduce correlation risk"
                ]
            },
            "risk_assessment": {
                "stress_level": "manageable" if estimated_loss < portfolio_value * 0.1 else "concerning" if estimated_loss < portfolio_value * 0.2 else "severe",
                "recommendation": "Monitor closely" if estimated_loss < portfolio_value * 0.1 else "Consider risk reduction"
            }
        }
    
    # Performance Tracking Tools Implementation
    async def get_agent_performance(self, agent_id: str, period: str = "1m", metrics: List[str] = None) -> Dict[str, Any]:
        """Get comprehensive agent performance metrics"""
        if metrics is None:
            metrics = ["return", "sharpe", "max_drawdown", "win_rate", "profit_factor"]
        
        # Mock performance data
        performance_data = {
            "agent_id": agent_id,
            "period": period,
            "metrics": {
                "total_return": 0.15,  # 15%
                "annualized_return": 0.18,
                "sharpe_ratio": 1.85,
                "sortino_ratio": 2.12,
                "max_drawdown": 0.08,
                "win_rate": 0.68,
                "profit_factor": 1.45,
                "calmar_ratio": 2.25,
                "information_ratio": 0.75
            },
            "trading_statistics": {
                "total_trades": 245,
                "winning_trades": 167,
                "losing_trades": 78,
                "avg_win": 0.024,  # 2.4%
                "avg_loss": -0.015,  # -1.5%
                "largest_win": 0.087,
                "largest_loss": -0.045,
                "avg_holding_period_hours": 18.5
            },
            "risk_metrics": {
                "volatility": 0.16,
                "beta": 1.12,
                "var_95": 0.025,
                "expected_shortfall": 0.035,
                "tail_ratio": 0.85
            },
            "consistency_metrics": {
                "winning_months": 8,
                "losing_months": 4,
                "best_month": 0.12,
                "worst_month": -0.06,
                "consistency_score": 0.78
            }
        }
        
        return performance_data
    
    async def compare_strategy_performance(self, strategies: List[str], period: str = "1m", benchmark: str = "SPY") -> Dict[str, Any]:
        """Compare performance of different strategies"""
        # Mock strategy comparison
        strategy_data = {}
        
        for i, strategy in enumerate(strategies):
            base_return = 0.10 + (i * 0.03)  # Varying returns
            strategy_data[strategy] = {
                "total_return": base_return,
                "sharpe_ratio": 1.5 + (i * 0.2),
                "max_drawdown": 0.08 + (i * 0.02),
                "volatility": 0.15 + (i * 0.03),
                "win_rate": 0.65 + (i * 0.05),
                "total_trades": 200 + (i * 50)
            }
        
        # Benchmark data
        benchmark_data = {
            "total_return": 0.08,
            "sharpe_ratio": 1.2,
            "max_drawdown": 0.12,
            "volatility": 0.18,
            "win_rate": 0.60
        }
        
        # Rankings
        rankings = {
            "by_return": sorted(strategies, key=lambda s: strategy_data[s]["total_return"], reverse=True),
            "by_sharpe": sorted(strategies, key=lambda s: strategy_data[s]["sharpe_ratio"], reverse=True),
            "by_risk_adjusted": sorted(strategies, key=lambda s: strategy_data[s]["total_return"] / strategy_data[s]["max_drawdown"], reverse=True)
        }
        
        return {
            "comparison_period": period,
            "benchmark": benchmark,
            "benchmark_data": benchmark_data,
            "strategies": strategy_data,
            "rankings": rankings,
            "analysis": {
                "best_overall": rankings["by_risk_adjusted"][0],
                "highest_return": rankings["by_return"][0],
                "best_risk_adjusted": rankings["by_sharpe"][0],
                "outperforming_benchmark": len([s for s in strategies if strategy_data[s]["total_return"] > benchmark_data["total_return"]])
            }
        }
    
    def get_tools_registry(self) -> Dict[str, Any]:
        """Get the tools registry for LLM integration"""
        return {
            "tools": [
                {
                    "name": tool_name,
                    "description": tool_config["description"],
                    "parameters": tool_config["parameters"],
                    "type": tool_config["type"].value
                }
                for tool_name, tool_config in self.tools_registry.items()
            ],
            "total_tools": len(self.tools_registry),
            "tool_categories": list(set([tool["type"].value for tool in self.tools_registry.values()]))
        }

# Global tools instance
tools = AgentTradingTools()

# API Endpoints
@app.get("/")
async def root():
    return {
        "service": "Agent Trading Tools MCP Server",
        "version": "2.0.0",
        "status": "active",
        "total_tools": len(tools.tools_registry),
        "capabilities": ["market_analysis", "trade_execution", "portfolio_management", "risk_assessment", "performance_tracking"]
    }

@app.get("/tools")
async def get_tools_registry():
    """Get all available tools for LLM integration"""
    return tools.get_tools_registry()

@app.post("/execute_tool")
async def execute_tool_endpoint(tool_name: str, parameters: Dict[str, Any]):
    """Execute a specific tool with parameters"""
    result = await tools.execute_tool(tool_name, parameters)
    return asdict(result)

@app.get("/tools/{tool_name}")
async def get_tool_info(tool_name: str):
    """Get information about a specific tool"""
    if tool_name not in tools.tools_registry:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    return tools.tools_registry[tool_name]

@app.get("/performance")
async def get_tools_performance():
    """Get tools performance metrics"""
    return {
        "total_executions": len(tools.execution_history),
        "recent_executions": tools.execution_history[-10:],  # Last 10 executions
        "average_execution_time": sum([exec["execution_time_ms"] for exec in tools.execution_history]) / len(tools.execution_history) if tools.execution_history else 0,
        "success_rate": len([exec for exec in tools.execution_history if exec["success"]]) / len(tools.execution_history) if tools.execution_history else 1.0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")
