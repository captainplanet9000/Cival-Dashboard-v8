# MCP Trading Platform - API Documentation

## Overview

This document provides comprehensive API documentation for all services in the MCP Trading Platform. Each service exposes REST APIs following OpenAPI 3.0 specifications with consistent response formats and error handling.

## Common API Patterns

### Base URL Structure
```
http://localhost:{port}/
```

### Authentication
Most endpoints require JWT authentication:
```http
Authorization: Bearer <jwt_token>
```

### Response Format
All APIs return JSON responses with consistent structure:
```json
{
  "status": "success|error",
  "data": {...},
  "message": "Human readable message",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Error Handling
Standard HTTP status codes with detailed error messages:
- `200 OK`: Successful request
- `400 Bad Request`: Invalid input parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Core Services APIs

### Market Data Server (Port 8001)

#### Health Check
```http
GET /health
```
Returns service health status and capabilities.

#### Get Market Data
```http
GET /market-data/{symbol}
```
**Parameters:**
- `symbol` (string): Trading symbol (e.g., "AAPL")

**Response:**
```json
{
  "symbol": "AAPL",
  "price": 150.25,
  "bid": 150.20,
  "ask": 150.30,
  "volume": 1000000,
  "timestamp": "2024-01-01T15:30:00Z"
}
```

#### Stream Market Data
```http
WebSocket /ws/market-data
```
Real-time market data streaming via WebSocket.

### Historical Data Server (Port 8002)

#### Get Historical Data
```http
GET /historical/{symbol}
```
**Parameters:**
- `symbol` (string): Trading symbol
- `start_date` (string): Start date (YYYY-MM-DD)
- `end_date` (string): End date (YYYY-MM-DD)
- `interval` (string): Data interval (1m, 5m, 1h, 1d)

**Response:**
```json
{
  "symbol": "AAPL",
  "data": [
    {
      "timestamp": "2024-01-01T09:30:00Z",
      "open": 149.50,
      "high": 150.75,
      "low": 149.25,
      "close": 150.25,
      "volume": 50000
    }
  ]
}
```

### Trading Engine (Port 8010)

#### Submit Order
```http
POST /orders
```
**Request Body:**
```json
{
  "symbol": "AAPL",
  "side": "buy|sell",
  "quantity": 100,
  "order_type": "market|limit|stop",
  "price": 150.00,
  "strategy_id": "momentum_1"
}
```

**Response:**
```json
{
  "order_id": "ord_123456",
  "status": "submitted",
  "symbol": "AAPL",
  "side": "buy",
  "quantity": 100,
  "timestamp": "2024-01-01T15:30:00Z"
}
```

#### Get Order Status
```http
GET /orders/{order_id}
```
Returns current order status and execution details.

### Order Management (Port 8011)

#### List Orders
```http
GET /orders
```
**Parameters:**
- `status` (string): Filter by order status
- `symbol` (string): Filter by symbol
- `limit` (int): Maximum number of orders to return

#### Cancel Order
```http
DELETE /orders/{order_id}
```
Cancels an open order.

### Risk Management (Port 8012)

#### Risk Check
```http
POST /risk/check
```
**Request Body:**
```json
{
  "portfolio_id": "port_123",
  "proposed_trade": {
    "symbol": "AAPL",
    "side": "buy",
    "quantity": 1000
  }
}
```

**Response:**
```json
{
  "approved": true,
  "risk_score": 0.75,
  "warnings": [],
  "limits_breached": []
}
```

#### Get Risk Metrics
```http
GET /risk/metrics/{portfolio_id}
```
Returns current risk metrics for a portfolio.

### Portfolio Tracker (Port 8013)

#### Get Portfolio Positions
```http
GET /portfolio/{portfolio_id}/positions
```
Returns current portfolio positions and P&L.

#### Get Portfolio Performance
```http
GET /portfolio/{portfolio_id}/performance
```
Returns portfolio performance metrics and analytics.

## Intelligence Services APIs

### Octagon Intelligence (Port 8020)

#### Get Market Intelligence
```http
GET /intelligence/market/{symbol}
```
Returns comprehensive market intelligence and insights.

#### Generate Investment Ideas
```http
POST /intelligence/ideas
```
**Request Body:**
```json
{
  "universe": ["AAPL", "GOOGL", "MSFT"],
  "risk_tolerance": "moderate",
  "investment_horizon": "6M"
}
```

### MongoDB Intelligence (Port 8021)

#### Query Market Insights
```http
POST /insights/query
```
**Request Body:**
```json
{
  "query": {
    "symbol": "AAPL",
    "timeframe": "1M"
  },
  "filters": {
    "min_confidence": 0.7
  }
}
```

### Neo4j Intelligence (Port 8022)

#### Analyze Relationships
```http
GET /relationships/{symbol}
```
Returns relationship analysis and network effects.

## Analytics & AI Services APIs

### AI Prediction Engine (Port 8050)

#### Get Price Predictions
```http
GET /predictions/{symbol}
```
**Parameters:**
- `horizon` (string): Prediction horizon (1h, 1d, 1w)
- `model` (string): Model type (lstm, transformer, ensemble)

**Response:**
```json
{
  "symbol": "AAPL",
  "predictions": [
    {
      "timestamp": "2024-01-02T09:30:00Z",
      "predicted_price": 151.25,
      "confidence": 0.85,
      "model": "ensemble"
    }
  ]
}
```

#### Train Model
```http
POST /models/train
```
**Request Body:**
```json
{
  "model_type": "lstm",
  "symbols": ["AAPL", "GOOGL"],
  "features": ["price", "volume", "technical_indicators"],
  "training_period": "2Y"
}
```

### Technical Analysis Engine (Port 8051)

#### Get Technical Analysis
```http
GET /analysis/{symbol}
```
Returns comprehensive technical analysis with indicators and patterns.

#### Calculate Indicators
```http
POST /indicators/calculate
```
**Request Body:**
```json
{
  "symbol": "AAPL",
  "indicators": ["RSI", "MACD", "Bollinger_Bands"],
  "period": "1M"
}
```

### ML Portfolio Optimizer (Port 8052)

#### Optimize Portfolio
```http
POST /optimization/optimize
```
**Request Body:**
```json
{
  "objective": "max_sharpe",
  "universe": ["AAPL", "GOOGL", "MSFT"],
  "constraints": {
    "max_weight": 0.3,
    "min_weight": 0.05
  },
  "lookback_period": "2Y"
}
```

**Response:**
```json
{
  "optimal_weights": {
    "AAPL": 0.25,
    "GOOGL": 0.35,
    "MSFT": 0.40
  },
  "expected_return": 0.12,
  "expected_risk": 0.18,
  "sharpe_ratio": 0.67
}
```

#### Get Efficient Frontier
```http
GET /optimization/efficient-frontier
```
Returns efficient frontier analysis for portfolio optimization.

### Sentiment Analysis Engine (Port 8053)

#### Analyze Text Sentiment
```http
POST /sentiment/analyze
```
**Request Body:**
```json
{
  "text": "Apple reports record quarterly earnings beating analyst expectations",
  "language": "en",
  "include_entities": true,
  "include_emotions": true
}
```

**Response:**
```json
{
  "sentiment_score": 0.75,
  "sentiment_polarity": "positive",
  "confidence": 0.89,
  "key_phrases": ["record quarterly earnings", "beating expectations"],
  "entities": [
    {"type": "COMPANY", "value": "Apple", "confidence": 0.95}
  ],
  "emotions": {
    "joy": 0.8,
    "trust": 0.7,
    "anticipation": 0.6
  }
}
```

#### Get News Sentiment
```http
GET /sentiment/news/{symbol}
```
Returns aggregated news sentiment for a symbol.

## Performance & Infrastructure APIs

### Optimization Engine (Port 8060)

#### Get Performance Metrics
```http
GET /metrics
```
Returns system performance metrics and optimization recommendations.

#### Configure Optimization
```http
POST /optimization/configure
```
**Request Body:**
```json
{
  "cache_config": {
    "l1_size": "1GB",
    "l2_size": "10GB",
    "ttl": 3600
  },
  "optimization_targets": ["latency", "throughput"]
}
```

### Load Balancer (Port 8070)

#### Get Load Balancer Status
```http
GET /status
```
Returns load balancer status and backend health.

#### Configure Load Balancing
```http
POST /configure
```
**Request Body:**
```json
{
  "algorithm": "weighted_round_robin",
  "health_check_interval": 30,
  "auto_scaling": {
    "enabled": true,
    "min_instances": 2,
    "max_instances": 10
  }
}
```

### Performance Monitor (Port 8080)

#### Get System Metrics
```http
GET /metrics
```
Returns comprehensive system performance metrics.

#### Generate Performance Report
```http
GET /reports/performance
```
**Parameters:**
- `timeframe` (string): Report timeframe (1h, 1d, 1w)
- `format` (string): Report format (json, pdf)

## Advanced Features APIs

### Trading Strategies Framework (Port 8090)

#### Create Strategy
```http
POST /strategies
```
**Request Body:**
```json
{
  "name": "Momentum Strategy",
  "type": "momentum",
  "parameters": {
    "lookback_period": 20,
    "volume_threshold": 1.5,
    "rsi_threshold": 60
  },
  "universe": ["AAPL", "GOOGL", "MSFT"],
  "capital_allocation": 0.25
}
```

#### Generate Signals
```http
POST /strategies/{strategy_id}/signals
```
Generates trading signals for a specific strategy.

#### Run Backtest
```http
POST /backtests
```
**Request Body:**
```json
{
  "strategy_id": "strat_123",
  "start_date": "2023-01-01",
  "end_date": "2024-01-01",
  "initial_capital": 1000000,
  "commission_rate": 0.001
}
```

### Advanced Risk Management (Port 8091)

#### Calculate VaR
```http
POST /var/calculate
```
**Request Body:**
```json
{
  "portfolio_id": "port_123",
  "method": "historical",
  "confidence_level": 0.95,
  "time_horizon": 1,
  "lookback_days": 252
}
```

**Response:**
```json
{
  "var_amount": 50000,
  "var_percentage": 5.0,
  "expected_shortfall": 75000,
  "confidence_level": 0.95,
  "method": "historical"
}
```

#### Run Stress Test
```http
POST /stress-test
```
**Request Body:**
```json
{
  "portfolio_id": "port_123",
  "scenario_ids": ["2008_crisis", "covid_crash"],
  "include_correlation_breakdown": true
}
```

### Market Microstructure (Port 8092)

#### Get Order Flow Metrics
```http
GET /order-flow/{symbol}
```
**Parameters:**
- `timeframe` (string): Analysis timeframe (1m, 5m, 15m)

**Response:**
```json
{
  "symbol": "AAPL",
  "total_volume": 1000000,
  "buy_volume": 600000,
  "sell_volume": 400000,
  "order_imbalance": 0.2,
  "effective_spread": 0.02,
  "market_impact_metrics": {
    "avg_impact": 0.001,
    "max_impact": 0.005
  }
}
```

#### Get Liquidity Metrics
```http
GET /liquidity/{symbol}
```
Returns comprehensive liquidity metrics for a symbol.

### External Data Integration (Port 8093)

#### Add Data Provider
```http
POST /providers
```
**Request Body:**
```json
{
  "name": "Alpha Vantage",
  "type": "market_data",
  "base_url": "https://www.alphavantage.co/query",
  "auth_type": "api_key",
  "auth_config": {
    "api_key": "your_api_key"
  },
  "rate_limits": {
    "per_minute": 5,
    "per_day": 500
  }
}
```

#### Query External Data
```http
POST /data/query
```
**Request Body:**
```json
{
  "provider_id": "provider_123",
  "endpoint": "TIME_SERIES_DAILY",
  "symbol": "AAPL",
  "parameters": {
    "outputsize": "compact"
  },
  "cache_duration": 300
}
```

## WebSocket APIs

### Real-Time Streaming

#### Market Data Stream
```javascript
const ws = new WebSocket('ws://localhost:8001/ws/market-data');

// Subscribe to symbols
ws.send(JSON.stringify({
  action: 'subscribe',
  symbols: ['AAPL', 'GOOGL', 'MSFT']
}));

// Receive real-time updates
ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Market data:', data);
};
```

#### Trading Signals Stream
```javascript
const ws = new WebSocket('ws://localhost:8090/ws');

// Receive real-time trading signals
ws.onmessage = function(event) {
  const signal = JSON.parse(event.data);
  if (signal.type === 'trading_signal') {
    console.log('New signal:', signal.data);
  }
};
```

#### Risk Alerts Stream
```javascript
const ws = new WebSocket('ws://localhost:8091/ws');

// Receive real-time risk alerts
ws.onmessage = function(event) {
  const alert = JSON.parse(event.data);
  if (alert.type === 'risk_alert') {
    console.log('Risk alert:', alert.data);
  }
};
```

## Rate Limiting

All APIs implement rate limiting to ensure fair usage:

- **Market Data**: 1000 requests/minute
- **Trading**: 500 requests/minute  
- **Analytics**: 200 requests/minute
- **Historical Data**: 100 requests/minute

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## SDK Examples

### Python SDK
```python
from mcp_trading import MCPClient

# Initialize client
client = MCPClient(base_url='http://localhost:8001', api_key='your_api_key')

# Get market data
market_data = client.market_data.get('AAPL')

# Submit order
order = client.trading.submit_order(
    symbol='AAPL',
    side='buy',
    quantity=100,
    order_type='market'
)

# Get predictions
predictions = client.ai.get_predictions('AAPL', horizon='1d')
```

### JavaScript SDK
```javascript
import { MCPClient } from 'mcp-trading-js';

// Initialize client
const client = new MCPClient({
  baseURL: 'http://localhost:8001',
  apiKey: 'your_api_key'
});

// Get market data
const marketData = await client.marketData.get('AAPL');

// Submit order
const order = await client.trading.submitOrder({
  symbol: 'AAPL',
  side: 'buy',
  quantity: 100,
  orderType: 'market'
});

// Stream real-time data
client.stream.marketData(['AAPL', 'GOOGL'], (data) => {
  console.log('Real-time data:', data);
});
```

## Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| 1001 | Invalid symbol | Use valid trading symbol |
| 1002 | Insufficient funds | Add funds or reduce order size |
| 1003 | Market closed | Wait for market open |
| 1004 | Risk limit exceeded | Reduce position size |
| 1005 | Invalid order type | Use supported order types |
| 1006 | Data provider error | Check external data provider |
| 1007 | Model training failed | Check training parameters |
| 1008 | Optimization failed | Adjust optimization constraints |

## Testing

### API Testing
Use the provided test scripts to validate API functionality:

```bash
# Run integration tests
python tests/test_system_integration.py

# Run E2E tests
python tests/e2e_testing_framework.py

# Test specific service
curl -X GET "http://localhost:8001/health"
```

### Load Testing
Use Apache Bench or similar tools for load testing:

```bash
# Test market data endpoint
ab -n 1000 -c 10 http://localhost:8001/market-data/AAPL

# Test trading endpoint with POST
ab -n 100 -c 5 -p order.json -T application/json http://localhost:8010/orders
```

## Support

For API support and documentation updates:
- **Technical Support**: api-support@mcp-trading.com
- **Documentation**: https://docs.mcp-trading.com
- **GitHub Issues**: https://github.com/mcp-trading/platform/issues