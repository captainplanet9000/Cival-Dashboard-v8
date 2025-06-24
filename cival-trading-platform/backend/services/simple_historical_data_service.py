"""
Simple Historical Data Service (No External Dependencies)
Provides basic historical data functionality for testing
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)

class SimpleHistoricalDataService:
    """Simple historical data service without external dependencies"""
    
    def __init__(self):
        # Mock data cache
        self.cache = {}
        
        # Configuration
        self.supported_symbols = ['BTC-USD', 'ETH-USD', 'AAPL', 'TSLA', 'SPY']
        self.cache_ttl = 300  # 5 minutes
        
    async def get_historical_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> Optional[Dict[str, Any]]:
        """Get historical data for a symbol (mock implementation)"""
        try:
            # Generate mock historical data
            end_date = datetime.now(timezone.utc)
            
            # Determine number of data points based on period
            if period == "1d":
                days = 1
            elif period == "1w":
                days = 7
            elif period == "1mo":
                days = 30
            elif period == "3mo":
                days = 90
            elif period == "6mo":
                days = 180
            elif period == "1y":
                days = 365
            else:
                days = 30
            
            # Generate mock price data
            import random
            base_price = 100.0
            if symbol == 'BTC-USD':
                base_price = 45000.0
            elif symbol == 'ETH-USD':
                base_price = 2500.0
            elif symbol == 'AAPL':
                base_price = 175.0
            elif symbol == 'TSLA':
                base_price = 200.0
            elif symbol == 'SPY':
                base_price = 450.0
            
            data = []
            current_price = base_price
            
            for i in range(days):
                date = end_date - timedelta(days=days-i-1)
                
                # Random walk with slight upward bias
                change_pct = random.uniform(-0.05, 0.06)  # -5% to +6%
                current_price = current_price * (1 + change_pct)
                
                # Ensure price doesn't go negative
                current_price = max(current_price, 0.01)
                
                volume = random.randint(1000000, 10000000)
                
                data.append({
                    'date': date.isoformat(),
                    'open': round(current_price * 0.99, 2),
                    'high': round(current_price * 1.02, 2),
                    'low': round(current_price * 0.98, 2),
                    'close': round(current_price, 2),
                    'volume': volume
                })
            
            return {
                'symbol': symbol,
                'period': period,
                'interval': interval,
                'data': data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return None
    
    async def get_current_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current price for a symbol"""
        try:
            # Mock current prices
            mock_prices = {
                'BTC-USD': 45234.56,
                'ETH-USD': 2567.89,
                'AAPL': 178.45,
                'TSLA': 203.67,
                'SPY': 452.34
            }
            
            base_price = mock_prices.get(symbol, 100.0)
            
            # Add some random variation
            import random
            variation = random.uniform(-0.02, 0.02)  # ±2%
            current_price = base_price * (1 + variation)
            
            return {
                'symbol': symbol,
                'price': round(current_price, 2),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'mock'
            }
            
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    async def get_volatility(self, symbol: str) -> float:
        """Calculate volatility for a symbol (mock implementation)"""
        try:
            # Mock volatility data
            mock_volatilities = {
                'BTC-USD': 0.65,  # 65% annualized
                'ETH-USD': 0.75,  # 75% annualized
                'AAPL': 0.25,     # 25% annualized
                'TSLA': 0.45,     # 45% annualized
                'SPY': 0.15       # 15% annualized
            }
            
            return mock_volatilities.get(symbol, 0.30)  # Default 30%
            
        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {e}")
            return 0.30
    
    async def get_supported_symbols(self) -> List[str]:
        """Get list of supported symbols"""
        return self.supported_symbols
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            "service": "simple_historical_data_service",
            "status": "running",
            "supported_symbols": len(self.supported_symbols),
            "cache_size": len(self.cache),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_simple_historical_data_service():
    """Factory function to create SimpleHistoricalDataService instance"""
    return SimpleHistoricalDataService()