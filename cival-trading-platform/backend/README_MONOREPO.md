# MCP Trading Platform - Monorepo v2.0.0

**Consolidated AI-Powered Algorithmic Trading Platform for Agent Operations**

## 🚀 Overview

This is the consolidated monorepo version of the MCP Trading Platform, transforming 20+ microservices into a unified application optimized for agent trading operations and Railway deployment.

### Key Improvements

- **Single Application**: Consolidated from 20+ services (ports 8001-8100) to one unified FastAPI app
- **Agent Trading Ready**: Direct operational bridge between AI agents and live trading
- **Railway Optimized**: Configured for seamless Railway cloud deployment
- **70% Resource Reduction**: Eliminated inter-service network overhead
- **Sub-100ms Agent Communication**: In-process service calls vs network requests

## 🏗️ Architecture

### Service Consolidation
```
Before: 20+ microservices on different ports
After:  Single FastAPI app with internal service modules
Result: Simplified deployment, faster agent coordination
```

### Core Components

- **Core Registry**: Centralized service and dependency management
- **Database Manager**: Unified connection pooling for Supabase, Redis, SQLAlchemy
- **Service Initializer**: Orchestrated startup with dependency resolution
- **Agent Framework**: Integrated CrewAI and AutoGen for trading operations

## 🔧 Quick Start

### Prerequisites

- Python 3.11+
- Railway account
- Supabase database
- Redis Cloud instance

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Run the platform**:
   ```bash
   python main_consolidated.py
   ```

4. **Access the API**:
   - Platform: http://localhost:8000
   - Health Check: http://localhost:8000/health
   - Documentation: http://localhost:8000/docs

### Railway Deployment

1. **Connect Railway to your repository**
2. **Set environment variables** in Railway dashboard:
   ```
   SUPABASE_URL=https://nmzuamwzbjlfhbqbvvpf.supabase.co
   SUPABASE_ANON_KEY=your_supabase_key
   REDIS_URL=your_redis_cloud_url
   ENVIRONMENT=production
   PORT=8000
   ```

3. **Deploy automatically** - Railway will use the provided configuration files

## 🤖 Agent Trading Operations

### Agent Management

Create and manage trading agents:
```python
POST /api/v1/agents
{
  "name": "BTC Momentum Agent",
  "strategy": {
    "strategy_name": "momentum_trading",
    "watched_symbols": ["BTC/USD"]
  },
  "risk_config": {
    "max_capital_allocation_usd": 1000,
    "risk_per_trade_percentage": 0.02
  }
}
```

### Start Agent Trading
```python
POST /api/v1/agents/{agent_id}/start
```

### Execute Trades (Agent → Market)
```python
POST /api/v1/agents/execute-trade
{
  "source_agent_id": "agent_123",
  "trade_params": {
    "symbol": "BTC/USD",
    "side": "buy",
    "quantity": 0.01,
    "order_type": "market"
  }
}
```

## 📊 Available Endpoints

### Core Platform
- `GET /` - Platform information
- `GET /health` - Comprehensive health check
- `GET /api/v1/debug/services` - Service status (dev only)

### Market Data
- `GET /api/v1/market-data/live/{symbol}` - Real-time data
- `GET /api/v1/market-data/historical/{symbol}` - Historical data

### Trading Operations
- `POST /api/v1/trading/orders` - Create orders
- `GET /api/v1/trading/orders` - Get user orders
- `GET /api/v1/portfolio/positions` - Portfolio positions
- `GET /api/v1/risk/assessment` - Risk analysis

### Agent Management
- `POST /api/v1/agents` - Create agent
- `GET /api/v1/agents` - List agents
- `POST /api/v1/agents/{id}/start` - Start agent
- `POST /api/v1/agents/{id}/stop` - Stop agent
- `POST /api/v1/agents/execute-trade` - Execute agent trade

### AI & Analytics
- `POST /api/v1/ai/predict/{symbol}` - AI predictions
- `GET /api/v1/analytics/technical/{symbol}` - Technical analysis
- `GET /api/v1/analytics/sentiment/{symbol}` - Sentiment analysis

### Real-time Streaming
- `GET /api/v1/stream/agent-events` - Agent status updates (SSE)

## 🔒 Security & Safety

### Trading Safety Controls
- Position size validation based on account equity
- Real-time risk monitoring with automatic limits
- Circuit breakers for abnormal conditions
- Trade approval workflow for high-impact decisions

### Authentication
- JWT-based authentication with role-based access
- Service-to-service authentication for agent operations
- Secure API key management

## 🌊 Environment Configuration

### Required Environment Variables

```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
DATABASE_URL=postgresql://... (optional, uses Supabase if not set)

# Cache
REDIS_URL=redis://your-redis-cloud-url

# Application
ENVIRONMENT=production
PORT=8000
LOG_LEVEL=INFO

# Trading (Optional)
HYPERLIQUID_API_KEY=your_api_key
HYPERLIQUID_SECRET=your_secret
```

### Optional Variables

```bash
# Security
JWT_SECRET=your_jwt_secret
FRONTEND_URL=https://your-frontend.com

# Development
SQL_ECHO=false
DEBUG=false
```

## 📈 Monitoring & Observability

### Health Monitoring
- `/health` endpoint provides comprehensive status
- Service-level health checks for all components
- Connection health for databases and cache

### Logging
- Structured JSON logging
- Configurable log levels
- Error tracking and alerting

### Real-time Monitoring
- Agent performance tracking
- Trade execution monitoring
- Risk exposure dashboards

## 🔄 Migration from Microservices

If migrating from the original microservices architecture:

1. **Backup Data**: Export all existing data from microservices
2. **Update Configuration**: Use new consolidated environment variables
3. **Test Agents**: Verify agent configurations work with new API endpoints
4. **Deploy**: Use Railway configuration for seamless deployment
5. **Monitor**: Watch health checks and agent performance

## 🛠️ Development

### Adding New Services

1. **Create Service Class** in `services/`
2. **Register in Service Initializer** (`core/service_initializer.py`)
3. **Add API Endpoints** in `main_consolidated.py`
4. **Add Health Checks** for monitoring

### Service Dependencies

Services are initialized in dependency order:
1. Core Infrastructure (market data, historical data)
2. Trading Engine (portfolio, trading, orders, risk)
3. AI & Analytics (prediction, technical, sentiment)
4. Agent & Execution (specialist, hyperliquid, agents)
5. Business Logic (strategy, watchlist, preferences)
6. Agent Frameworks (CrewAI, AutoGen)

## 🚨 Troubleshooting

### Common Issues

1. **Service Initialization Errors**:
   - Check environment variables
   - Verify database connections
   - Review service logs

2. **Agent Trading Issues**:
   - Verify agent configuration
   - Check risk management settings
   - Review execution logs

3. **Database Connection Problems**:
   - Validate Supabase URL and key
   - Check Redis connection
   - Review network connectivity

### Debug Endpoints

- `GET /api/v1/debug/services` - Service status
- `GET /api/v1/debug/health-detailed` - Detailed health info

## 📞 Support

- GitHub Issues: [Repository Issues](https://github.com/captainplanet9000/mcp-trading-platform/issues)
- Documentation: See `/docs` endpoint when running
- Health Status: Always check `/health` for system status

## 🎯 Production Deployment Checklist

- [ ] Environment variables configured in Railway
- [ ] Supabase database tables created
- [ ] Redis Cloud instance configured
- [ ] Health check endpoint responding
- [ ] Agent configurations tested
- [ ] Risk management limits set
- [ ] Monitoring dashboards configured
- [ ] Backup procedures established

---

**MCP Trading Platform v2.0.0** - Consolidated for Agent Trading Excellence 🚀