# 🚀 Railway Deployment Guide
## Complete Autonomous Trading System with AG-UI, MCP, Farms, Goals, Wallets

### 📋 Overview

Your autonomous trading system is now configured for Railway deployment with the following components:

- **Backend**: FastAPI with MCP service registry
- **Frontend**: AG-UI React interface  
- **Database**: Supabase PostgreSQL
- **Cache**: Railway Redis
- **AI**: OpenRouter multi-LLM integration
- **Trading**: Hyperliquid & DEX support
- **Architecture**: Complete monorepo deployment

### 🗂️ Deployment Files Created

```
├── .env.railway          # Environment variables template
├── railway.json          # Railway service configuration  
├── Procfile             # Process definition
├── nixpacks.toml        # Build optimization
└── verify_railway_deployment.py  # Deployment verification
```

### 🔧 Pre-Deployment Setup

#### 1. Database Setup (Supabase)
```bash
# Already created in Supabase:
# - All trading system tables
# - RLS policies configured
# - API keys generated
```

#### 2. Get Required API Keys
```bash
# OpenRouter (LLM Services)
export OPENROUTER_API_KEY="your-key"

# Hyperliquid (Trading)
export HYPERLIQUID_API_KEY="your-key"
export HYPERLIQUID_SECRET_KEY="your-secret"

# Additional APIs (optional)
export NEWS_API_KEY="your-key"
export COINGECKO_API_KEY="your-key"
```

#### 3. Generate Security Keys
```bash
# JWT Secret (Python)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# API Key
python -c "import secrets; print(secrets.token_hex(32))"

# Session Secret  
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 🌐 Railway Deployment Steps

#### 1. Create Railway Project
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Create new project
railway up

# Link to existing project (if created via dashboard)
railway link [project-id]
```

#### 2. Configure Environment Variables

Copy from `.env.railway` and set in Railway dashboard:

**Essential Variables:**
```bash
# Database
DATABASE_URL=postgresql://postgres:[password]@[project-ref].supabase.co:5432/postgres?sslmode=require
SUPABASE_URL=https://[project-ref].supabase.co
SUPABASE_ANON_KEY=[your-anon-key]
SUPABASE_SERVICE_ROLE_KEY=[your-service-role-key]

# Security
JWT_SECRET_KEY=[generated-secret]
API_KEY=[generated-api-key]  
SESSION_SECRET=[generated-session-secret]

# AI Services
OPENROUTER_API_KEY=[your-openrouter-key]

# Trading (Start with paper trading)
TRADING_ENABLED=true
PAPER_TRADING_MODE=true
LIVE_TRADING_ENABLED=false

# Application
ENVIRONMENT=production
APP_PORT=8000
CORS_ORIGINS=https://[your-domain].railway.app
```

#### 3. Add Railway Plugins
```bash
# Add Redis (required for caching)
railway add redis

# Add PostgreSQL (if not using Supabase)  
railway add postgresql
```

#### 4. Deploy Application
```bash
# Deploy from current directory
railway up

# Or deploy from GitHub
# 1. Connect GitHub repo in Railway dashboard
# 2. Push to main branch
# 3. Railway auto-deploys
```

### 🔍 Verification & Testing

#### 1. Run Pre-Deployment Check
```bash
python verify_railway_deployment.py
```

#### 2. Test Deployed Application
```bash
# Health check
curl https://[your-domain].railway.app/health

# API endpoints
curl https://[your-domain].railway.app/api/v1/agents
curl https://[your-domain].railway.app/api/v1/farms
curl https://[your-domain].railway.app/api/v1/goals

# WebSocket connection
# Test via browser console or WebSocket client
```

#### 3. Monitor Deployment
```bash
# View logs
railway logs

# Check status
railway status

# Monitor resources
# Visit Railway dashboard for metrics
```

### 📊 System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AG-UI React   │◄──►│   FastAPI MCP    │◄──►│   Supabase DB   │
│   Frontend      │    │   Backend        │    │   PostgreSQL    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  OpenRouter AI  │◄──►│  Service Registry│◄──►│  Railway Redis  │
│  Multi-LLM      │    │  (MCP Core)      │    │  Cache Layer    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Hyperliquid    │◄──►│  Agent Farm      │◄──►│  Goal System    │  
│  Exchange       │    │  Management      │    │  Autonomous     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 🛡️ Security Configuration

#### Production Security Checklist:
- ✅ JWT secret keys generated
- ✅ CORS origins restricted  
- ✅ SSL/HTTPS enabled
- ✅ Secure cookies enabled
- ✅ API rate limiting configured
- ✅ Database credentials secured
- ✅ No secrets in code repository

#### Environment Security:
```bash
# Production settings
SECURE_COOKIES=true
SSL_REDIRECT=true
CSRF_PROTECTION=true
CORS_ORIGINS=https://[your-domain].railway.app

# Development/staging (disable for testing)
DEBUG=false
TESTING_MODE=false
MOCK_EXTERNAL_APIS=false
```

### 🎯 Trading System Configuration

#### Safe Production Start:
```bash
# Start with paper trading
TRADING_ENABLED=true
PAPER_TRADING_MODE=true  
LIVE_TRADING_ENABLED=false

# Risk management enabled
RISK_MANAGEMENT_ENABLED=true
MAX_POSITION_SIZE=1000
MAX_DAILY_TRADES=50
MAX_DRAWDOWN_THRESHOLD=0.05
```

#### Agent Configuration:
```bash
# Agent limits
MAX_AGENTS=100
MAX_FARMS=10
MAX_AGENTS_PER_FARM=20

# Strategy distribution
DARVAS_BOX_AGENTS=10
WILLIAMS_ALLIGATOR_AGENTS=10  
ELLIOTT_WAVE_AGENTS=5
RENKO_AGENTS=8
HEIKIN_ASHI_AGENTS=8
```

#### Goal System:
```bash
# Goal management
MAX_ACTIVE_GOALS=50
AUTONOMOUS_GOAL_CREATION=true
GOAL_COMPLETION_TIMEOUT=86400

# Target goals
PROFIT_GOALS_ENABLED=true
TRADE_COUNT_GOALS_ENABLED=true
```

### 📈 Monitoring & Maintenance

#### Application Monitoring:
- Health endpoint: `/health`
- Metrics endpoint: `/metrics` 
- Real-time logs in Railway dashboard
- Performance monitoring enabled

#### Key Metrics to Watch:
- Response times (<500ms target)
- Memory usage (<2GB limit)
- CPU usage (<80% limit)  
- Trade execution success rate
- Agent performance metrics
- Goal completion rates

#### Automated Tasks:
- Health checks every 5 minutes
- Performance reports every 6 hours
- Database backups daily at 2 AM
- Log cleanup weekly

### 🚨 Troubleshooting

#### Common Issues:

**Deployment Fails:**
```bash
# Check logs
railway logs

# Verify environment variables
railway variables

# Check build process
# Review nixpacks.toml configuration
```

**Database Connection Issues:**
```bash
# Verify DATABASE_URL format
# Check Supabase project status
# Verify SSL certificate settings
# Test connection from Railway shell
```

**API Errors:**
```bash
# Check OpenRouter API key
# Verify rate limits not exceeded
# Check CORS configuration
# Test endpoints individually
```

**WebSocket Connection Fails:**
```bash
# Verify WebSocket enabled in environment
# Check proxy configuration
# Test with simple WebSocket client
# Review Railway networking settings
```

### 🎉 Success Criteria

Your deployment is successful when:

- ✅ Health endpoint returns 200 OK
- ✅ All API endpoints accessible  
- ✅ WebSocket connections work
- ✅ Agent system initializes
- ✅ Farm management operational
- ✅ Goal system functional
- ✅ Paper trading executes
- ✅ Frontend loads and connects
- ✅ Real-time updates flowing
- ✅ Performance within targets

### 🔄 Post-Deployment Tasks

1. **Enable Live Trading** (when ready):
   ```bash
   PAPER_TRADING_MODE=false
   LIVE_TRADING_ENABLED=true
   ```

2. **Scale Resources** (if needed):
   - Increase memory/CPU in Railway dashboard
   - Add additional replicas for high load
   - Optimize database queries

3. **Set Up Monitoring**:
   - Configure alerting webhooks
   - Set up log aggregation
   - Monitor trading performance
   - Track goal achievement rates

4. **Optimize Performance**:
   - Review slow API endpoints
   - Optimize database queries
   - Cache frequently accessed data
   - Monitor agent resource usage

### 📞 Support & Resources

- **Railway Documentation**: https://docs.railway.app
- **Supabase Documentation**: https://supabase.com/docs  
- **OpenRouter API**: https://openrouter.ai/docs
- **Hyperliquid API**: https://hyperliquid.gitbook.io/hyperliquid-docs

For issues with this deployment configuration, check:
1. Railway deployment logs
2. Environment variable configuration
3. Network connectivity tests
4. API rate limits and quotas

---

## 🎯 Next Steps

Your autonomous trading system is now Railway-ready! The monorepo architecture ensures single-deployment simplicity while maintaining the complete feature set including AG-UI, MCP backend, farm management, goal system, and master wallet functionality.

Start with paper trading, monitor performance, and gradually enable live trading features as confidence grows.