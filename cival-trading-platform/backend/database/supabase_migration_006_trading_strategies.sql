-- Phase 10: Advanced Multi-Agent Trading Strategies Database Schema
-- Sophisticated trading strategies, market analysis, and portfolio coordination

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Trading Strategies Table
CREATE TABLE IF NOT EXISTS trading_strategies (
    strategy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL CHECK (strategy_type IN (
        'momentum', 'mean_reversion', 'arbitrage', 'market_making', 'breakout',
        'scalping', 'swing', 'grid', 'dca', 'pairs', 'statistical_arbitrage',
        'news_sentiment', 'technical_indicator', 'machine_learning', 'multi_factor'
    )),
    
    -- Configuration
    parameters JSONB DEFAULT '{}'::jsonb,
    timeframes JSONB DEFAULT '[]'::jsonb,
    symbols JSONB DEFAULT '[]'::jsonb,
    
    -- Risk management
    max_position_size DECIMAL(20,8) NOT NULL,
    max_portfolio_allocation DECIMAL(5,4) CHECK (max_portfolio_allocation >= 0.0 AND max_portfolio_allocation <= 1.0),
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('very_low', 'low', 'moderate', 'high', 'very_high')),
    stop_loss_percentage DECIMAL(5,4),
    take_profit_percentage DECIMAL(5,4),
    
    -- Market conditions
    preferred_conditions JSONB DEFAULT '[]'::jsonb,
    min_volatility DECIMAL(8,6),
    max_volatility DECIMAL(8,6),
    
    -- Performance targets
    target_sharpe_ratio DECIMAL(8,4),
    max_drawdown DECIMAL(5,4),
    target_win_rate DECIMAL(5,4),
    
    -- Status and metadata
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_modified TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,
    
    -- Performance data
    backtest_results JSONB DEFAULT '{}'::jsonb,
    live_performance JSONB DEFAULT '{}'::jsonb
);

-- Trading Signals Table
CREATE TABLE IF NOT EXISTS trading_signals (
    signal_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID NOT NULL REFERENCES trading_strategies(strategy_id) ON DELETE CASCADE,
    agent_id UUID,
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('buy', 'sell', 'hold')),
    strength VARCHAR(20) NOT NULL CHECK (strength IN ('very_weak', 'weak', 'moderate', 'strong', 'very_strong')),
    confidence DECIMAL(3,2) NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    
    -- Signal details
    entry_price DECIMAL(20,8),
    target_price DECIMAL(20,8),
    stop_loss DECIMAL(20,8),
    quantity DECIMAL(20,8),
    position_side VARCHAR(10) NOT NULL CHECK (position_side IN ('long', 'short', 'neutral')),
    
    -- Context
    timeframe VARCHAR(10) NOT NULL,
    market_condition VARCHAR(20) NOT NULL CHECK (market_condition IN (
        'bullish', 'bearish', 'sideways', 'volatile', 'low_volatility', 
        'high_volatility', 'trending', 'consolidating'
    )),
    technical_indicators JSONB DEFAULT '{}'::jsonb,
    fundamental_factors JSONB DEFAULT '{}'::jsonb,
    
    -- Metadata
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    priority INTEGER CHECK (priority >= 1 AND priority <= 10) DEFAULT 5,
    
    -- Validation criteria
    min_market_cap DECIMAL(20,2),
    max_spread DECIMAL(8,6),
    required_volume DECIMAL(20,8),
    
    -- Status
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'executed', 'expired', 'cancelled'))
);

-- Trading Positions Table  
CREATE TABLE IF NOT EXISTS trading_positions (
    position_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID NOT NULL REFERENCES trading_strategies(strategy_id),
    agent_id UUID,
    symbol VARCHAR(20) NOT NULL,
    
    -- Position details
    side VARCHAR(10) NOT NULL CHECK (side IN ('long', 'short', 'neutral')),
    quantity DECIMAL(20,8) NOT NULL,
    entry_price DECIMAL(20,8) NOT NULL,
    current_price DECIMAL(20,8),
    
    -- Risk management
    stop_loss DECIMAL(20,8),
    take_profit DECIMAL(20,8),
    trailing_stop_distance DECIMAL(8,6),
    
    -- Status
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'closed', 'partial')),
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    
    -- Performance
    unrealized_pnl DECIMAL(20,8) DEFAULT 0,
    realized_pnl DECIMAL(20,8) DEFAULT 0,
    fees_paid DECIMAL(20,8) DEFAULT 0,
    
    -- Metadata
    tags JSONB DEFAULT '[]'::jsonb,
    notes TEXT DEFAULT ''
);

-- Portfolio Allocations Table
CREATE TABLE IF NOT EXISTS portfolio_allocations (
    allocation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL,
    portfolio_name VARCHAR(255) NOT NULL,
    
    -- Strategy allocations
    strategy_allocations JSONB DEFAULT '{}'::jsonb,
    symbol_allocations JSONB DEFAULT '{}'::jsonb,
    
    -- Risk constraints
    max_single_position DECIMAL(3,2) DEFAULT 0.10 CHECK (max_single_position >= 0.0 AND max_single_position <= 1.0),
    max_sector_exposure DECIMAL(3,2) DEFAULT 0.30 CHECK (max_sector_exposure >= 0.0 AND max_sector_exposure <= 1.0),
    max_correlation DECIMAL(3,2) DEFAULT 0.70 CHECK (max_correlation >= 0.0 AND max_correlation <= 1.0),
    
    -- Rebalancing
    rebalance_frequency VARCHAR(20) DEFAULT 'daily' CHECK (rebalance_frequency IN ('real_time', 'hourly', 'daily', 'weekly', 'monthly')),
    rebalance_threshold DECIMAL(5,4) DEFAULT 0.05,
    
    -- Target metrics
    target_volatility DECIMAL(8,6),
    target_return DECIMAL(8,6),
    max_drawdown_limit DECIMAL(5,4) DEFAULT 0.20,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_rebalanced TIMESTAMPTZ,
    created_by UUID
);

-- Multi-Agent Coordination Table
CREATE TABLE IF NOT EXISTS multi_agent_coordination (
    coordination_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    
    -- Participating strategies/agents
    participating_strategies JSONB DEFAULT '[]'::jsonb,
    coordinator_agent_id UUID,
    
    -- Coordination rules
    signal_aggregation VARCHAR(50) DEFAULT 'weighted_average' CHECK (signal_aggregation IN ('majority_vote', 'weighted_average', 'consensus')),
    conflict_resolution VARCHAR(50) DEFAULT 'priority_based' CHECK (conflict_resolution IN ('priority_based', 'risk_adjusted', 'performance_based')),
    
    -- Signal handling
    min_signal_consensus DECIMAL(3,2) DEFAULT 0.60 CHECK (min_signal_consensus >= 0.0 AND min_signal_consensus <= 1.0),
    signal_timeout INTEGER DEFAULT 300,
    
    -- Risk management
    aggregate_position_limits JSONB DEFAULT '{}'::jsonb,
    correlation_monitoring BOOLEAN DEFAULT TRUE,
    max_simultaneous_trades INTEGER DEFAULT 10,
    
    -- Performance tracking
    coordination_performance JSONB DEFAULT '{}'::jsonb,
    
    -- Status
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Arbitrage Opportunities Table
CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
    opportunity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Opportunity details
    arbitrage_type VARCHAR(50) NOT NULL CHECK (arbitrage_type IN ('spatial', 'temporal', 'triangular', 'statistical')),
    symbols JSONB NOT NULL,
    exchanges JSONB NOT NULL,
    
    -- Price differences
    price_differential DECIMAL(20,8) NOT NULL,
    percentage_spread DECIMAL(8,6) NOT NULL,
    expected_profit DECIMAL(20,8) NOT NULL,
    
    -- Execution requirements
    minimum_volume DECIMAL(20,8) NOT NULL,
    execution_window INTEGER NOT NULL, -- seconds
    required_capital DECIMAL(20,8) NOT NULL,
    
    -- Risk factors
    execution_risk DECIMAL(3,2) CHECK (execution_risk >= 0.0 AND execution_risk <= 1.0),
    liquidity_risk DECIMAL(3,2) CHECK (liquidity_risk >= 0.0 AND liquidity_risk <= 1.0),
    timing_risk DECIMAL(3,2) CHECK (timing_risk >= 0.0 AND timing_risk <= 1.0),
    
    -- Status
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'executed', 'expired')),
    
    -- Validation
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    historical_success_rate DECIMAL(3,2) CHECK (historical_success_rate >= 0.0 AND historical_success_rate <= 1.0)
);

-- Risk Metrics Table
CREATE TABLE IF NOT EXISTS risk_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL,
    calculation_timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    -- Portfolio metrics
    total_value DECIMAL(20,8) NOT NULL,
    total_exposure DECIMAL(20,8) NOT NULL,
    leverage DECIMAL(8,4) NOT NULL,
    
    -- Risk measures
    var_1day DECIMAL(20,8), -- Value at Risk
    var_5day DECIMAL(20,8),
    expected_shortfall DECIMAL(20,8),
    max_drawdown DECIMAL(5,4),
    current_drawdown DECIMAL(5,4),
    
    -- Volatility metrics
    portfolio_volatility DECIMAL(8,6),
    beta DECIMAL(8,4),
    correlation_matrix JSONB DEFAULT '{}'::jsonb,
    
    -- Concentration risk
    largest_position_weight DECIMAL(5,4),
    top_5_concentration DECIMAL(5,4),
    sector_concentrations JSONB DEFAULT '{}'::jsonb,
    
    -- Liquidity metrics
    liquidity_score DECIMAL(3,2) CHECK (liquidity_score >= 0.0 AND liquidity_score <= 1.0),
    days_to_liquidate DECIMAL(8,2),
    
    -- Performance attribution
    strategy_contributions JSONB DEFAULT '{}'::jsonb,
    factor_exposures JSONB DEFAULT '{}'::jsonb
);

-- Strategy Performance Table
CREATE TABLE IF NOT EXISTS strategy_performance (
    performance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID NOT NULL REFERENCES trading_strategies(strategy_id),
    performance_period VARCHAR(20) NOT NULL CHECK (performance_period IN ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')),
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    
    -- Return metrics
    total_return DECIMAL(8,6),
    annualized_return DECIMAL(8,6),
    excess_return DECIMAL(8,6), -- vs benchmark
    
    -- Risk metrics
    volatility DECIMAL(8,6),
    sharpe_ratio DECIMAL(8,4),
    sortino_ratio DECIMAL(8,4),
    calmar_ratio DECIMAL(8,4),
    
    -- Drawdown analysis
    max_drawdown DECIMAL(5,4),
    average_drawdown DECIMAL(5,4),
    drawdown_duration INTEGER, -- days
    
    -- Trade statistics
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate DECIMAL(5,4),
    average_win DECIMAL(8,6),
    average_loss DECIMAL(8,6),
    profit_factor DECIMAL(8,4),
    
    -- Risk-adjusted metrics
    information_ratio DECIMAL(8,4),
    treynor_ratio DECIMAL(8,4),
    jensen_alpha DECIMAL(8,6),
    
    -- Consistency metrics
    monthly_returns JSONB DEFAULT '[]'::jsonb,
    hit_ratio DECIMAL(5,4), -- percentage of positive periods
    
    calculated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Market Regimes Table
CREATE TABLE IF NOT EXISTS market_regimes (
    regime_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Regime characteristics
    regime_name VARCHAR(100) NOT NULL,
    market_condition VARCHAR(20) NOT NULL CHECK (market_condition IN (
        'bullish', 'bearish', 'sideways', 'volatile', 'low_volatility', 
        'high_volatility', 'trending', 'consolidating'
    )),
    volatility_level VARCHAR(20) CHECK (volatility_level IN ('low', 'medium', 'high')),
    trend_direction VARCHAR(20) CHECK (trend_direction IN ('up', 'down', 'sideways')),
    
    -- Market metrics
    average_volatility DECIMAL(8,6),
    correlation_levels JSONB DEFAULT '{}'::jsonb,
    liquidity_conditions VARCHAR(20) CHECK (liquidity_conditions IN ('high', 'medium', 'low')),
    
    -- Strategy performance in regime
    strategy_performance JSONB DEFAULT '{}'::jsonb,
    recommended_strategies JSONB DEFAULT '[]'::jsonb,
    strategies_to_avoid JSONB DEFAULT '[]'::jsonb,
    
    -- Regime detection
    confidence DECIMAL(3,2) CHECK (confidence >= 0.0 AND confidence <= 1.0),
    detection_signals JSONB DEFAULT '[]'::jsonb,
    
    -- Timing
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    expected_duration_hours INTEGER,
    
    -- Historical analysis
    historical_frequency DECIMAL(5,4),
    average_duration_days DECIMAL(8,2),
    
    -- Status
    active BOOLEAN DEFAULT TRUE
);

-- Adaptive Learning Table
CREATE TABLE IF NOT EXISTS adaptive_learning (
    learning_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id UUID NOT NULL REFERENCES trading_strategies(strategy_id),
    
    -- Learning parameters
    learning_rate DECIMAL(5,4) DEFAULT 0.01 CHECK (learning_rate >= 0.0 AND learning_rate <= 1.0),
    adaptation_frequency VARCHAR(20) DEFAULT 'daily' CHECK (adaptation_frequency IN ('real_time', 'hourly', 'daily', 'weekly')),
    lookback_period INTEGER DEFAULT 30, -- days
    
    -- Feature selection
    features_to_monitor JSONB DEFAULT '[]'::jsonb,
    feature_importance JSONB DEFAULT '{}'::jsonb,
    
    -- Model parameters
    model_type VARCHAR(50) DEFAULT 'ensemble' CHECK (model_type IN ('linear', 'tree', 'neural_network', 'ensemble')),
    retrain_threshold DECIMAL(5,4) DEFAULT 0.05, -- performance degradation threshold
    
    -- Performance tracking
    prediction_accuracy DECIMAL(5,4) DEFAULT 0.0,
    adaptation_history JSONB DEFAULT '[]'::jsonb,
    
    -- Configuration
    auto_adaptation BOOLEAN DEFAULT TRUE,
    require_approval BOOLEAN DEFAULT FALSE,
    min_confidence_threshold DECIMAL(3,2) DEFAULT 0.70,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_adaptation TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Market Data Table (for historical storage)
CREATE TABLE IF NOT EXISTS market_data (
    data_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    timeframe VARCHAR(10) NOT NULL, -- 1m, 5m, 15m, 1h, 4h, 1d
    
    -- OHLCV data
    open_price DECIMAL(20,8) NOT NULL,
    high_price DECIMAL(20,8) NOT NULL,
    low_price DECIMAL(20,8) NOT NULL,
    close_price DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    
    -- Additional metrics
    vwap DECIMAL(20,8),
    twap DECIMAL(20,8),
    bid DECIMAL(20,8),
    ask DECIMAL(20,8),
    spread DECIMAL(8,6),
    
    -- Technical indicators
    rsi DECIMAL(8,4),
    macd JSONB,
    bollinger_bands JSONB,
    moving_averages JSONB DEFAULT '{}'::jsonb,
    
    -- Market metrics
    market_cap DECIMAL(20,2),
    circulating_supply DECIMAL(20,8),
    volatility DECIMAL(8,6),
    
    UNIQUE(symbol, timestamp, timeframe)
);

-- Create indexes for optimal performance

-- Trading Strategies indexes
CREATE INDEX IF NOT EXISTS idx_trading_strategies_type ON trading_strategies(strategy_type);
CREATE INDEX IF NOT EXISTS idx_trading_strategies_active ON trading_strategies(active);
CREATE INDEX IF NOT EXISTS idx_trading_strategies_created ON trading_strategies(created_at);

-- Trading Signals indexes
CREATE INDEX IF NOT EXISTS idx_trading_signals_strategy ON trading_signals(strategy_id);
CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol ON trading_signals(symbol);
CREATE INDEX IF NOT EXISTS idx_trading_signals_status ON trading_signals(status);
CREATE INDEX IF NOT EXISTS idx_trading_signals_generated ON trading_signals(generated_at);
CREATE INDEX IF NOT EXISTS idx_trading_signals_expires ON trading_signals(expires_at);
CREATE INDEX IF NOT EXISTS idx_trading_signals_strength ON trading_signals(strength);

-- Trading Positions indexes
CREATE INDEX IF NOT EXISTS idx_trading_positions_strategy ON trading_positions(strategy_id);
CREATE INDEX IF NOT EXISTS idx_trading_positions_symbol ON trading_positions(symbol);
CREATE INDEX IF NOT EXISTS idx_trading_positions_status ON trading_positions(status);
CREATE INDEX IF NOT EXISTS idx_trading_positions_opened ON trading_positions(opened_at);
CREATE INDEX IF NOT EXISTS idx_trading_positions_agent ON trading_positions(agent_id);

-- Portfolio Allocations indexes
CREATE INDEX IF NOT EXISTS idx_portfolio_allocations_portfolio ON portfolio_allocations(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_allocations_created ON portfolio_allocations(created_at);
CREATE INDEX IF NOT EXISTS idx_portfolio_allocations_rebalanced ON portfolio_allocations(last_rebalanced);

-- Multi-Agent Coordination indexes
CREATE INDEX IF NOT EXISTS idx_coordination_active ON multi_agent_coordination(active);
CREATE INDEX IF NOT EXISTS idx_coordination_coordinator ON multi_agent_coordination(coordinator_agent_id);

-- Arbitrage Opportunities indexes
CREATE INDEX IF NOT EXISTS idx_arbitrage_type ON arbitrage_opportunities(arbitrage_type);
CREATE INDEX IF NOT EXISTS idx_arbitrage_status ON arbitrage_opportunities(status);
CREATE INDEX IF NOT EXISTS idx_arbitrage_detected ON arbitrage_opportunities(detected_at);
CREATE INDEX IF NOT EXISTS idx_arbitrage_expires ON arbitrage_opportunities(expires_at);

-- Risk Metrics indexes
CREATE INDEX IF NOT EXISTS idx_risk_metrics_portfolio ON risk_metrics(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_risk_metrics_timestamp ON risk_metrics(calculation_timestamp);

-- Strategy Performance indexes
CREATE INDEX IF NOT EXISTS idx_performance_strategy ON strategy_performance(strategy_id);
CREATE INDEX IF NOT EXISTS idx_performance_period ON strategy_performance(performance_period);
CREATE INDEX IF NOT EXISTS idx_performance_dates ON strategy_performance(start_date, end_date);

-- Market Regimes indexes
CREATE INDEX IF NOT EXISTS idx_regimes_condition ON market_regimes(market_condition);
CREATE INDEX IF NOT EXISTS idx_regimes_active ON market_regimes(active);
CREATE INDEX IF NOT EXISTS idx_regimes_detected ON market_regimes(detected_at);

-- Adaptive Learning indexes
CREATE INDEX IF NOT EXISTS idx_adaptive_strategy ON adaptive_learning(strategy_id);
CREATE INDEX IF NOT EXISTS idx_adaptive_auto ON adaptive_learning(auto_adaptation);
CREATE INDEX IF NOT EXISTS idx_adaptive_last ON adaptive_learning(last_adaptation);

-- Market Data indexes
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time ON market_data(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_market_data_timeframe ON market_data(timeframe);
CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_strategies_name_search ON trading_strategies USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));
CREATE INDEX IF NOT EXISTS idx_signals_symbol_search ON trading_signals USING gin(to_tsvector('english', symbol));

-- JSONB indexes for complex queries
CREATE INDEX IF NOT EXISTS idx_strategies_parameters_gin ON trading_strategies USING gin(parameters);
CREATE INDEX IF NOT EXISTS idx_signals_technical_gin ON trading_signals USING gin(technical_indicators);
CREATE INDEX IF NOT EXISTS idx_allocations_strategies_gin ON portfolio_allocations USING gin(strategy_allocations);
CREATE INDEX IF NOT EXISTS idx_coordination_strategies_gin ON multi_agent_coordination USING gin(participating_strategies);

-- Row Level Security (RLS) Policies

-- Enable RLS on all tables
ALTER TABLE trading_strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE multi_agent_coordination ENABLE ROW LEVEL SECURITY;
ALTER TABLE arbitrage_opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategy_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_regimes ENABLE ROW LEVEL SECURITY;
ALTER TABLE adaptive_learning ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_data ENABLE ROW LEVEL SECURITY;

-- Create policies for authenticated users
CREATE POLICY "Users can manage trading strategies" ON trading_strategies
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Users can manage trading signals" ON trading_signals
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Users can manage trading positions" ON trading_positions
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Users can manage portfolio allocations" ON portfolio_allocations
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Users can manage coordination" ON multi_agent_coordination
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Users can view arbitrage opportunities" ON arbitrage_opportunities
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Users can view risk metrics" ON risk_metrics
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Users can view strategy performance" ON strategy_performance
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Users can view market regimes" ON market_regimes
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Users can manage adaptive learning" ON adaptive_learning
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Users can view market data" ON market_data
    FOR SELECT USING (auth.role() = 'authenticated');

-- Create updated_at triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_trading_strategies_updated_at BEFORE UPDATE ON trading_strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_multi_agent_coordination_updated_at BEFORE UPDATE ON multi_agent_coordination
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_adaptive_learning_updated_at BEFORE UPDATE ON adaptive_learning
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create functions for common operations

-- Function to calculate strategy performance metrics
CREATE OR REPLACE FUNCTION calculate_strategy_performance(strategy_uuid UUID, start_date TIMESTAMPTZ, end_date TIMESTAMPTZ)
RETURNS JSONB AS $$
DECLARE
    performance_data JSONB;
    total_trades INTEGER;
    winning_trades INTEGER;
    total_return DECIMAL;
    win_rate DECIMAL;
BEGIN
    SELECT 
        COUNT(*),
        COUNT(*) FILTER (WHERE realized_pnl > 0),
        COALESCE(SUM(realized_pnl), 0)
    INTO total_trades, winning_trades, total_return
    FROM trading_positions
    WHERE strategy_id = strategy_uuid
    AND closed_at BETWEEN start_date AND end_date
    AND status = 'closed';
    
    IF total_trades = 0 THEN
        win_rate := 0.0;
    ELSE
        win_rate := (winning_trades::DECIMAL / total_trades::DECIMAL) * 100;
    END IF;
    
    performance_data := jsonb_build_object(
        'total_trades', total_trades,
        'winning_trades', winning_trades,
        'losing_trades', total_trades - winning_trades,
        'total_return', total_return,
        'win_rate', ROUND(win_rate, 2),
        'calculated_at', NOW()
    );
    
    RETURN performance_data;
END;
$$ LANGUAGE plpgsql;

-- Function to get active signals for a strategy
CREATE OR REPLACE FUNCTION get_active_signals(strategy_uuid UUID)
RETURNS JSONB AS $$
DECLARE
    signals JSONB;
BEGIN
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'signal_id', signal_id,
                'symbol', symbol,
                'signal_type', signal_type,
                'strength', strength,
                'confidence', confidence,
                'generated_at', generated_at
            )
        ), 
        '[]'::jsonb
    )
    INTO signals
    FROM trading_signals
    WHERE strategy_id = strategy_uuid
    AND status = 'active'
    AND (expires_at IS NULL OR expires_at > NOW())
    ORDER BY generated_at DESC;
    
    RETURN signals;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate portfolio risk metrics
CREATE OR REPLACE FUNCTION calculate_portfolio_risk(portfolio_uuid UUID)
RETURNS JSONB AS $$
DECLARE
    risk_data JSONB;
    total_value DECIMAL;
    total_positions INTEGER;
    largest_position DECIMAL;
BEGIN
    SELECT 
        COALESCE(SUM(ABS(quantity * current_price)), 0),
        COUNT(*),
        COALESCE(MAX(ABS(quantity * current_price)), 0)
    INTO total_value, total_positions, largest_position
    FROM trading_positions tp
    JOIN portfolio_allocations pa ON tp.strategy_id = ANY(
        SELECT jsonb_object_keys(pa.strategy_allocations)::UUID
        WHERE pa.portfolio_id = portfolio_uuid
    )
    WHERE tp.status = 'open';
    
    risk_data := jsonb_build_object(
        'total_value', total_value,
        'total_positions', total_positions,
        'largest_position_value', largest_position,
        'largest_position_weight', 
            CASE WHEN total_value > 0 THEN ROUND((largest_position / total_value) * 100, 2) ELSE 0 END,
        'calculated_at', NOW()
    );
    
    RETURN risk_data;
END;
$$ LANGUAGE plpgsql;

-- Insert sample data for development

-- Sample trading strategies
INSERT INTO trading_strategies (name, description, strategy_type, max_position_size, max_portfolio_allocation, risk_level)
VALUES 
    ('BTC Momentum Strategy', 'Bitcoin momentum trading using RSI and moving averages', 'momentum', 10000, 0.20, 'moderate'),
    ('ETH Mean Reversion', 'Ethereum mean reversion strategy with Bollinger Bands', 'mean_reversion', 5000, 0.15, 'low'),
    ('Multi-Asset Arbitrage', 'Cross-exchange arbitrage opportunities', 'arbitrage', 50000, 0.30, 'high'),
    ('Grid Trading Bot', 'Automated grid trading for stable coins', 'grid', 20000, 0.25, 'moderate');

-- Sample portfolio allocation
INSERT INTO portfolio_allocations (portfolio_id, portfolio_name, max_single_position, max_sector_exposure)
VALUES 
    (uuid_generate_v4(), 'Diversified Crypto Portfolio', 0.10, 0.30);

-- Sample market regime
INSERT INTO market_regimes (regime_name, market_condition, volatility_level, trend_direction, confidence)
VALUES 
    ('Bull Market 2024', 'bullish', 'medium', 'up', 0.85);

-- Commit the migration
COMMENT ON TABLE trading_strategies IS 'Trading strategy definitions and configurations';
COMMENT ON TABLE trading_signals IS 'Generated trading signals from strategies';
COMMENT ON TABLE trading_positions IS 'Active and historical trading positions';
COMMENT ON TABLE portfolio_allocations IS 'Portfolio allocation strategies and constraints';
COMMENT ON TABLE multi_agent_coordination IS 'Multi-agent coordination configurations';
COMMENT ON TABLE arbitrage_opportunities IS 'Detected arbitrage opportunities';
COMMENT ON TABLE risk_metrics IS 'Portfolio and strategy risk metrics';
COMMENT ON TABLE strategy_performance IS 'Historical strategy performance analytics';
COMMENT ON TABLE market_regimes IS 'Market regime classifications and characteristics';
COMMENT ON TABLE adaptive_learning IS 'Adaptive learning configurations for strategies';
COMMENT ON TABLE market_data IS 'Historical market data storage';