"""
Historical Data Service
Provides historical market data for trading analysis and backtesting
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import pandas as pd
import yfinance as yf
from decimal import Decimal

logger = logging.getLogger(__name__)

class HistoricalDataService:
    """Service for fetching and managing historical market data"""
    
    def __init__(self, market_data_service=None):
        self.market_data_service = market_data_service
        self.cache = {}
        self.cache_duration = timedelta(hours=1)
        
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "1y", 
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Get historical data for a symbol
        
        Args:
            symbol: Trading symbol (e.g., "BTC-USD", "AAPL")
            period: Time period (1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max)
            interval: Data interval (1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo)
        """
        try:
            cache_key = f"{symbol}_{period}_{interval}"
            
            # Check cache first
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if datetime.now(timezone.utc) - cached_time < self.cache_duration:
                    return cached_data
            
            # Fetch from Yahoo Finance
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(f"No historical data found for {symbol}")
                return None
            
            # Cache the data
            self.cache[cache_key] = (data, datetime.now(timezone.utc))
            
            logger.info(f"Retrieved historical data for {symbol}: {len(data)} records")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None
    
    async def get_price_history(
        self, 
        symbol: str, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get price history as a list of dictionaries"""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if data.empty:
                return []
            
            history = []
            for date, row in data.iterrows():
                history.append({
                    'timestamp': date.isoformat(),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume'])
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error fetching price history for {symbol}: {e}")
            return []
    
    async def get_returns(
        self, 
        symbol: str, 
        period: str = "1y"
    ) -> Optional[pd.Series]:
        """Calculate returns for a symbol"""
        try:
            data = await self.get_historical_data(symbol, period)
            if data is None or data.empty:
                return None
            
            returns = data['Close'].pct_change().dropna()
            return returns
            
        except Exception as e:
            logger.error(f"Error calculating returns for {symbol}: {e}")
            return None
    
    async def get_volatility(
        self, 
        symbol: str, 
        period: str = "1y"
    ) -> Optional[float]:
        """Calculate annualized volatility for a symbol"""
        try:
            returns = await self.get_returns(symbol, period)
            if returns is None or returns.empty:
                return None
            
            # Annualized volatility (assuming daily data)
            volatility = returns.std() * (252 ** 0.5)
            return float(volatility)
            
        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {e}")
            return None
    
    async def get_correlation_matrix(
        self, 
        symbols: List[str], 
        period: str = "1y"
    ) -> Optional[pd.DataFrame]:
        """Calculate correlation matrix for multiple symbols"""
        try:
            returns_data = {}
            
            for symbol in symbols:
                returns = await self.get_returns(symbol, period)
                if returns is not None and not returns.empty:
                    returns_data[symbol] = returns
            
            if not returns_data:
                return None
            
            # Align all series by date
            returns_df = pd.DataFrame(returns_data)
            correlation_matrix = returns_df.corr()
            
            return correlation_matrix
            
        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return None
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            "service": "historical_data_service",
            "status": "running",
            "cache_size": len(self.cache),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_historical_data_service():
    """Factory function to create HistoricalDataService instance"""
    return HistoricalDataService()