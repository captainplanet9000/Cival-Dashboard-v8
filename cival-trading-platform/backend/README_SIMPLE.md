# MCP Trading Platform - Simple Mode

This is a simplified version of the MCP Trading Platform that runs without complex external dependencies. It provides all the core API endpoints needed for the dashboard to function.

## 🚀 Quick Start

### Without External Dependencies
```bash
# Test the core services
python3 simple_main.py --test

# Run without FastAPI (basic mode)
python3 simple_main.py
```

### With FastAPI (if available)
```bash
# Install minimal dependencies
pip install fastapi uvicorn

# Run web server
python3 simple_main.py
```

## 📊 Available API Endpoints

### Core System
- `GET /` - System information
- `GET /health` - Health check
- `GET /api/v1/services` - List available services

### Market Data  
- `GET /api/v1/market-data/{symbol}` - Get market data for symbol
- `GET /api/v1/market/overview` - Market overview with major symbols

### Portfolio Management
- `GET /api/v1/portfolio/summary` - Portfolio summary
- `GET /api/v1/portfolio/positions` - Current positions

### Trading & Signals
- `GET /api/v1/trading/signals` - Recent trading signals
- `GET /api/v1/agents/status` - Trading agents status

### Performance
- `GET /api/v1/performance/metrics` - Performance metrics

## 🧪 Testing

```bash
# Test core functionality
python3 test_simple_services.py

# Test API endpoints (if FastAPI available)
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/portfolio/summary
curl http://localhost:8000/api/v1/market-data/BTC-USD
```

## 📁 File Structure

```
simple_main.py                     # Main application
simple_historical_data_service.py  # Core data service
test_simple_services.py            # Service tests
```

## 🔧 Technical Details

### Services Implemented
- **SimpleHistoricalDataService**: Provides mock historical data, current prices, and volatility
- **SimpleServiceRegistry**: Basic service registry for dependency injection

### Mock Data Provided
- Historical price data for major symbols (BTC-USD, ETH-USD, AAPL, TSLA, SPY)
- Current market prices with realistic variation
- Portfolio positions and P&L data
- Trading signals from multiple sources
- Agent status and performance metrics
- Market sentiment indicators

### No External Dependencies Required
- Uses only Python standard library
- Optional FastAPI for web server functionality
- Falls back to basic mode if FastAPI not available

## 🌐 Frontend Integration

The frontend dashboard can connect to these endpoints:

```javascript
// Example API calls
const portfolioData = await fetch('/api/v1/portfolio/summary');
const marketData = await fetch('/api/v1/market/overview');
const agentStatus = await fetch('/api/v1/agents/status');
```

## 🚀 Deployment

This simple version can be deployed anywhere Python is available:

```bash
# Railway, Heroku, etc.
python3 simple_main.py

# With gunicorn (if available)
gunicorn simple_main:app --host 0.0.0.0 --port $PORT
```

## 🔄 Upgrading to Full Version

To use the full version with all dependencies:

1. Install requirements: `pip install -r requirements.txt`
2. Configure environment variables in `.env`
3. Run: `python3 main_consolidated.py`

The API endpoints remain the same, so the frontend will work with either version.