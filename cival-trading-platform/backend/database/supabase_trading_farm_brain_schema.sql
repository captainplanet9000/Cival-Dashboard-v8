-- ==========================================
-- TRADING FARM BRAIN - COMPREHENSIVE ARCHIVE SCHEMA
-- Complete database schema for the Trading Farm Brain system
-- ==========================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ==========================================
-- CORE ARCHIVE TABLES
-- ==========================================

-- Master strategy registry with full lineage
CREATE TABLE IF NOT EXISTS farm_strategy_archive (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    strategy_type TEXT NOT NULL,
    version_number INTEGER NOT NULL DEFAULT 1,
    parent_strategy_id UUID REFERENCES farm_strategy_archive(id),
    
    -- Strategy definition
    strategy_code JSONB NOT NULL,          -- Complete strategy logic
    parameters JSONB NOT NULL,             -- All parameters and settings
    entry_conditions JSONB NOT NULL,       -- Entry logic
    exit_conditions JSONB NOT NULL,        -- Exit logic
    risk_rules JSONB NOT NULL,            -- Risk management rules
    
    -- Performance data
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    total_pnl DECIMAL(20,8) DEFAULT 0,
    max_drawdown DECIMAL(10,4) DEFAULT 0,
    sharpe_ratio DECIMAL(10,4) DEFAULT 0,
    win_rate DECIMAL(10,4) DEFAULT 0,
    
    -- Market context
    market_conditions JSONB DEFAULT '{}'::jsonb,               -- Market state when created
    asset_classes TEXT[] DEFAULT '{}',     -- Assets it trades
    timeframes TEXT[] DEFAULT '{}',        -- Timeframes it operates on
    
    -- Lifecycle
    created_by TEXT NOT NULL,              -- Agent or user who created it
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    retired_at TIMESTAMP WITH TIME ZONE,
    retirement_reason TEXT,
    
    -- Metadata
    tags TEXT[] DEFAULT '{}',
    description TEXT,
    notes JSONB DEFAULT '{}'::jsonb
);

-- Complete trade archive with full context
CREATE TABLE IF NOT EXISTS farm_trade_archive (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trade_id TEXT NOT NULL UNIQUE,
    
    -- Strategy context
    strategy_id UUID REFERENCES farm_strategy_archive(id),
    agent_id TEXT NOT NULL,
    
    -- Trade details
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,                    -- buy/sell/long/short
    quantity DECIMAL(20,8) NOT NULL,
    entry_price DECIMAL(20,8) NOT NULL,
    exit_price DECIMAL(20,8),
    
    -- Timing
    entry_time TIMESTAMP WITH TIME ZONE NOT NULL,
    exit_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    
    -- Financial results
    gross_pnl DECIMAL(20,8) DEFAULT 0,
    fees_paid DECIMAL(20,8) DEFAULT 0,
    net_pnl DECIMAL(20,8) DEFAULT 0,
    pnl_percentage DECIMAL(10,4) DEFAULT 0,
    
    -- Market context at entry
    entry_market_data JSONB NOT NULL,      -- Complete market state
    entry_indicators JSONB DEFAULT '{}'::jsonb,
    entry_sentiment JSONB DEFAULT '{}'::jsonb,
    
    -- Market context at exit
    exit_market_data JSONB DEFAULT '{}'::jsonb,
    exit_indicators JSONB DEFAULT '{}'::jsonb,
    exit_sentiment JSONB DEFAULT '{}'::jsonb,
    
    -- Decision context
    entry_reasoning TEXT,
    exit_reasoning TEXT,
    confidence_level DECIMAL(4,3),
    decision_factors JSONB DEFAULT '{}'::jsonb,
    
    -- Trade classification
    trade_type TEXT NOT NULL,              -- paper, live, backtest
    exchange TEXT,
    order_types JSONB DEFAULT '{}'::jsonb, -- order details
    
    -- Risk management
    stop_loss DECIMAL(20,8),
    take_profit DECIMAL(20,8),
    max_risk DECIMAL(20,8),
    position_size_logic JSONB DEFAULT '{}'::jsonb,
    
    -- Performance attribution
    strategy_contribution DECIMAL(10,4),
    market_contribution DECIMAL(10,4),
    luck_factor DECIMAL(10,4),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily trading farm summary
CREATE TABLE IF NOT EXISTS farm_daily_summary (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trading_date DATE NOT NULL UNIQUE,
    
    -- Overall performance
    total_pnl DECIMAL(20,8) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    gross_revenue DECIMAL(20,8) DEFAULT 0,
    total_fees DECIMAL(20,8) DEFAULT 0,
    net_profit DECIMAL(20,8) DEFAULT 0,
    
    -- Agent performance
    active_agents INTEGER DEFAULT 0,
    best_performing_agent TEXT,
    worst_performing_agent TEXT,
    agent_performance JSONB DEFAULT '{}'::jsonb,
    
    -- Strategy performance
    active_strategies INTEGER DEFAULT 0,
    best_performing_strategy TEXT,
    strategy_performance JSONB DEFAULT '{}'::jsonb,
    
    -- Market context
    market_conditions JSONB DEFAULT '{}'::jsonb,
    volatility_index DECIMAL(10,4),
    market_sentiment TEXT,
    
    -- Risk metrics
    max_drawdown DECIMAL(10,4) DEFAULT 0,
    var_95 DECIMAL(20,8) DEFAULT 0,
    sharpe_ratio DECIMAL(10,4) DEFAULT 0,
    
    -- Notable events
    significant_events JSONB DEFAULT '[]'::jsonb,
    alerts_triggered INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent decision archive with complete reasoning
CREATE TABLE IF NOT EXISTS farm_agent_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id TEXT NOT NULL UNIQUE,
    
    -- Agent context
    agent_id TEXT NOT NULL,
    agent_version TEXT,
    strategy_id UUID REFERENCES farm_strategy_archive(id),
    
    -- Decision details
    decision_type TEXT NOT NULL,           -- entry, exit, hold, rebalance
    symbol TEXT NOT NULL,
    decision_time TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Decision inputs
    market_data JSONB NOT NULL,
    technical_indicators JSONB DEFAULT '{}'::jsonb,
    fundamental_data JSONB DEFAULT '{}'::jsonb,
    sentiment_data JSONB DEFAULT '{}'::jsonb,
    news_events JSONB DEFAULT '[]'::jsonb,
    
    -- Decision process
    reasoning TEXT NOT NULL,
    confidence_score DECIMAL(4,3),
    alternative_considered JSONB DEFAULT '[]'::jsonb,
    risk_assessment JSONB DEFAULT '{}'::jsonb,
    
    -- Decision output
    recommended_action JSONB NOT NULL,
    expected_outcome JSONB DEFAULT '{}'::jsonb,
    position_sizing JSONB DEFAULT '{}'::jsonb,
    
    -- Execution details
    executed BOOLEAN DEFAULT FALSE,
    execution_delay_ms INTEGER,
    execution_details JSONB DEFAULT '{}'::jsonb,
    
    -- Outcome tracking
    actual_outcome JSONB DEFAULT '{}'::jsonb,
    outcome_vs_expected JSONB DEFAULT '{}'::jsonb,
    lessons_learned TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Market data archive for analysis
CREATE TABLE IF NOT EXISTS farm_market_archive (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    timeframe TEXT NOT NULL,              -- 1m, 5m, 1h, 1d, etc.
    
    -- OHLCV data
    open_price DECIMAL(20,8) NOT NULL,
    high_price DECIMAL(20,8) NOT NULL,
    low_price DECIMAL(20,8) NOT NULL,
    close_price DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    
    -- Derived metrics
    price_change DECIMAL(20,8),
    price_change_pct DECIMAL(10,4),
    volatility DECIMAL(10,4),
    
    -- Technical indicators
    indicators JSONB DEFAULT '{}'::jsonb,
    
    -- Market context
    exchange TEXT,
    market_cap DECIMAL(30,8),
    circulating_supply DECIMAL(30,8),
    
    -- External factors
    news_sentiment DECIMAL(4,3),
    social_sentiment DECIMAL(4,3),
    macro_factors JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Composite primary key for time series
    UNIQUE(symbol, timestamp, timeframe)
);

-- Agent memory persistence for Railway
CREATE TABLE IF NOT EXISTS farm_agent_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id TEXT NOT NULL,
    memory_type TEXT NOT NULL,            -- hot, warm, cold, semantic
    memory_key TEXT NOT NULL,
    
    -- Memory content
    memory_data JSONB NOT NULL,
    memory_embedding VECTOR(1536),        -- For semantic search
    
    -- Context
    created_context JSONB DEFAULT '{}'::jsonb,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Lifecycle
    expires_at TIMESTAMP WITH TIME ZONE,
    importance_score DECIMAL(4,3) DEFAULT 0.5,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure uniqueness per agent
    UNIQUE(agent_id, memory_type, memory_key)
);

-- Knowledge graph for strategy relationships
CREATE TABLE IF NOT EXISTS farm_knowledge_graph (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type TEXT NOT NULL,            -- strategy, trade, decision, market_event
    source_id UUID NOT NULL,
    target_type TEXT NOT NULL,
    target_id UUID NOT NULL,
    relationship_type TEXT NOT NULL,      -- derived_from, caused_by, similar_to, etc.
    
    -- Relationship strength and context
    strength DECIMAL(4,3) DEFAULT 0.5,
    context JSONB DEFAULT '{}'::jsonb,
    evidence JSONB DEFAULT '[]'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure no duplicate relationships
    UNIQUE(source_type, source_id, target_type, target_id, relationship_type)
);

-- User preferences and dashboard state persistence
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS dashboard_states (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    component_name TEXT NOT NULL,
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, component_name)
);

CREATE TABLE IF NOT EXISTS chart_configurations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chart_id TEXT NOT NULL,
    user_id UUID,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(chart_id, user_id)
);

CREATE TABLE IF NOT EXISTS agent_configurations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id TEXT NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    config_version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==========================================
-- PERFORMANCE INDEXES
-- ==========================================

-- Strategy archive indexes
CREATE INDEX IF NOT EXISTS idx_farm_strategy_type ON farm_strategy_archive(strategy_type);
CREATE INDEX IF NOT EXISTS idx_farm_strategy_created ON farm_strategy_archive(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_farm_strategy_performance ON farm_strategy_archive(total_pnl DESC);

-- Trade archive indexes  
CREATE INDEX IF NOT EXISTS idx_farm_trades_strategy ON farm_trade_archive(strategy_id);
CREATE INDEX IF NOT EXISTS idx_farm_trades_agent ON farm_trade_archive(agent_id);
CREATE INDEX IF NOT EXISTS idx_farm_trades_symbol ON farm_trade_archive(symbol);
CREATE INDEX IF NOT EXISTS idx_farm_trades_time ON farm_trade_archive(entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_farm_trades_pnl ON farm_trade_archive(net_pnl DESC);
CREATE INDEX IF NOT EXISTS idx_farm_trades_type ON farm_trade_archive(trade_type);

-- Decision archive indexes
CREATE INDEX IF NOT EXISTS idx_farm_decisions_agent ON farm_agent_decisions(agent_id);
CREATE INDEX IF NOT EXISTS idx_farm_decisions_time ON farm_agent_decisions(decision_time DESC);
CREATE INDEX IF NOT EXISTS idx_farm_decisions_type ON farm_agent_decisions(decision_type);
CREATE INDEX IF NOT EXISTS idx_farm_decisions_symbol ON farm_agent_decisions(symbol);

-- Market archive indexes
CREATE INDEX IF NOT EXISTS idx_farm_market_symbol_time ON farm_market_archive(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_farm_market_timeframe ON farm_market_archive(timeframe);

-- Memory indexes
CREATE INDEX IF NOT EXISTS idx_farm_memory_agent ON farm_agent_memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_farm_memory_type ON farm_agent_memory(memory_type);
CREATE INDEX IF NOT EXISTS idx_farm_memory_access ON farm_agent_memory(last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_farm_memory_importance ON farm_agent_memory(importance_score DESC);

-- Knowledge graph indexes
CREATE INDEX IF NOT EXISTS idx_farm_knowledge_source ON farm_knowledge_graph(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_farm_knowledge_target ON farm_knowledge_graph(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_farm_knowledge_relationship ON farm_knowledge_graph(relationship_type);

-- Daily summary indexes
CREATE INDEX IF NOT EXISTS idx_farm_daily_date ON farm_daily_summary(trading_date DESC);
CREATE INDEX IF NOT EXISTS idx_farm_daily_pnl ON farm_daily_summary(total_pnl DESC);

-- Configuration indexes
CREATE INDEX IF NOT EXISTS idx_user_prefs_user ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_states_user ON dashboard_states(user_id);
CREATE INDEX IF NOT EXISTS idx_chart_configs_chart ON chart_configurations(chart_id);
CREATE INDEX IF NOT EXISTS idx_agent_configs_agent ON agent_configurations(agent_id);

-- ==========================================
-- TRIGGERS AND FUNCTIONS
-- ==========================================

-- Updated at trigger function
CREATE OR REPLACE FUNCTION handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER handle_farm_strategy_updated_at
    BEFORE UPDATE ON farm_strategy_archive
    FOR EACH ROW
    EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER handle_farm_daily_updated_at
    BEFORE UPDATE ON farm_daily_summary
    FOR EACH ROW
    EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER handle_farm_memory_updated_at
    BEFORE UPDATE ON farm_agent_memory
    FOR EACH ROW
    EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER handle_user_prefs_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER handle_dashboard_states_updated_at
    BEFORE UPDATE ON dashboard_states
    FOR EACH ROW
    EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER handle_chart_configs_updated_at
    BEFORE UPDATE ON chart_configurations
    FOR EACH ROW
    EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER handle_agent_configs_updated_at
    BEFORE UPDATE ON agent_configurations
    FOR EACH ROW
    EXECUTE FUNCTION handle_updated_at();

-- ==========================================
-- ROW LEVEL SECURITY (RLS)
-- ==========================================

-- Enable RLS on all tables
ALTER TABLE farm_strategy_archive ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_trade_archive ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_daily_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_agent_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_market_archive ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_agent_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_knowledge_graph ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE chart_configurations ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_configurations ENABLE ROW LEVEL SECURITY;

-- Service role policies (for backend access)
CREATE POLICY "Service role access" ON farm_strategy_archive FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON farm_trade_archive FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON farm_daily_summary FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON farm_agent_decisions FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON farm_market_archive FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON farm_agent_memory FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON farm_knowledge_graph FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON user_preferences FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON dashboard_states FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON chart_configurations FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON agent_configurations FOR ALL USING (auth.role() = 'service_role');

-- Authenticated user policies (for frontend access)
CREATE POLICY "Authenticated read access" ON farm_strategy_archive FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated read access" ON farm_trade_archive FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated read access" ON farm_daily_summary FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated read access" ON farm_agent_decisions FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated read access" ON farm_market_archive FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated read access" ON farm_knowledge_graph FOR SELECT USING (auth.role() = 'authenticated');

-- ==========================================
-- SAMPLE DATA FOR TESTING
-- ==========================================

-- Insert sample strategy
INSERT INTO farm_strategy_archive (
    strategy_id, strategy_name, strategy_type, created_by,
    strategy_code, parameters, entry_conditions, exit_conditions, risk_rules
) VALUES (
    'momentum-v1',
    'Basic Momentum Strategy',
    'momentum',
    'system',
    '{"type": "momentum", "logic": "MA crossover with volume confirmation"}',
    '{"ma_short": 5, "ma_long": 20, "volume_threshold": 1.5}',
    '["MA5 > MA20", "Volume > 1.5x average"]',
    '["MA5 < MA20", "Stop loss triggered"]',
    '["Max 2% risk per trade", "Position size based on volatility"]'
) ON CONFLICT DO NOTHING;

-- Insert sample daily summary
INSERT INTO farm_daily_summary (
    trading_date, total_pnl, total_trades, winning_trades, active_agents
) VALUES (
    CURRENT_DATE,
    1250.75,
    15,
    9,
    3
) ON CONFLICT (trading_date) DO UPDATE SET
    total_pnl = EXCLUDED.total_pnl,
    total_trades = EXCLUDED.total_trades,
    winning_trades = EXCLUDED.winning_trades,
    active_agents = EXCLUDED.active_agents;

-- ==========================================
-- COMMENTS
-- ==========================================

COMMENT ON TABLE farm_strategy_archive IS 'Complete archive of all trading strategies with full lineage and performance data';
COMMENT ON TABLE farm_trade_archive IS 'Comprehensive trade archive with complete market context and decision reasoning';
COMMENT ON TABLE farm_daily_summary IS 'Daily aggregated performance summary for calendar dashboard';
COMMENT ON TABLE farm_agent_decisions IS 'Complete agent decision archive with reasoning and outcome tracking';
COMMENT ON TABLE farm_market_archive IS 'Market data archive for analysis and backtesting';
COMMENT ON TABLE farm_agent_memory IS 'Persistent agent memory for Railway deployment continuity';
COMMENT ON TABLE farm_knowledge_graph IS 'Relationship graph between strategies, trades, decisions, and market events';