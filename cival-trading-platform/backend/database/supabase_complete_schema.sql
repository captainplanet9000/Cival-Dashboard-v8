-- =============================================================================
-- COMPLETE AUTONOMOUS TRADING SYSTEM DATABASE SCHEMA
-- Supabase PostgreSQL Schema for Master Wallet, Farms, Goals, and Agents
-- =============================================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- =============================================================================
-- MASTER WALLET SYSTEM TABLES
-- =============================================================================

-- Master Wallets
CREATE TABLE IF NOT EXISTS master_wallets (
    wallet_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_name VARCHAR(255) NOT NULL,
    description TEXT,
    supported_chains TEXT[] DEFAULT ARRAY['ethereum', 'polygon', 'bsc', 'arbitrum'],
    auto_distribution BOOLEAN DEFAULT true,
    max_allocation_per_agent DECIMAL(3,2) DEFAULT 0.25,
    risk_tolerance DECIMAL(3,2) DEFAULT 0.7,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Wallet Addresses
CREATE TABLE IF NOT EXISTS wallet_addresses (
    address_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_id UUID REFERENCES master_wallets(wallet_id) ON DELETE CASCADE,
    address VARCHAR(42) NOT NULL,
    chain_id INTEGER NOT NULL,
    chain_name VARCHAR(50) NOT NULL,
    private_key_hash VARCHAR(64), -- Hashed for security
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(wallet_id, chain_name)
);

-- Wallet Balances
CREATE TABLE IF NOT EXISTS wallet_balances (
    balance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_id UUID REFERENCES master_wallets(wallet_id) ON DELETE CASCADE,
    asset_symbol VARCHAR(20) NOT NULL,
    balance DECIMAL(20,8) NOT NULL DEFAULT 0,
    available_balance DECIMAL(20,8) NOT NULL DEFAULT 0,
    balance_usd DECIMAL(20,2),
    chain_name VARCHAR(50) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(wallet_id, asset_symbol, chain_name)
);

-- Fund Allocations
CREATE TABLE IF NOT EXISTS fund_allocations (
    allocation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_id UUID REFERENCES master_wallets(wallet_id) ON DELETE CASCADE,
    target_type VARCHAR(50) NOT NULL CHECK (target_type IN ('agent', 'farm', 'goal', 'strategy')),
    target_id UUID NOT NULL,
    target_name VARCHAR(255) NOT NULL,
    allocated_amount_usd DECIMAL(20,2) NOT NULL,
    allocated_percentage DECIMAL(5,2) NOT NULL,
    current_value_usd DECIMAL(20,2) NOT NULL,
    initial_allocation DECIMAL(20,2) NOT NULL,
    total_pnl DECIMAL(20,2) DEFAULT 0,
    realized_pnl DECIMAL(20,2) DEFAULT 0,
    allocation_start TIMESTAMP WITH TIME ZONE DEFAULT now(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT now(),
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Fund Distribution Rules
CREATE TABLE IF NOT EXISTS fund_distribution_rules (
    rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_id UUID REFERENCES master_wallets(wallet_id) ON DELETE CASCADE,
    rule_name VARCHAR(255) NOT NULL,
    distribution_method VARCHAR(50) NOT NULL,
    conditions JSONB NOT NULL,
    parameters JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Wallet Transactions
CREATE TABLE IF NOT EXISTS wallet_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_id UUID REFERENCES master_wallets(wallet_id) ON DELETE CASCADE,
    transaction_type VARCHAR(50) NOT NULL,
    amount DECIMAL(20,8) NOT NULL,
    asset_symbol VARCHAR(20) NOT NULL,
    amount_usd DECIMAL(20,2),
    from_entity VARCHAR(255),
    to_entity VARCHAR(255),
    transaction_hash VARCHAR(66),
    chain_name VARCHAR(50),
    gas_used INTEGER,
    gas_price BIGINT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    confirmed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- =============================================================================
-- SMART CONTRACT SYSTEM TABLES
-- =============================================================================

-- Smart Contracts
CREATE TABLE IF NOT EXISTS smart_contracts (
    contract_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_type VARCHAR(50) NOT NULL,
    contract_address VARCHAR(42) NOT NULL,
    chain_id INTEGER NOT NULL,
    chain_name VARCHAR(50) NOT NULL,
    abi JSONB NOT NULL,
    deployment_block BIGINT,
    gas_limit INTEGER DEFAULT 300000,
    gas_price_multiplier DECIMAL(3,2) DEFAULT 1.1,
    is_active BOOLEAN DEFAULT true,
    deployed_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(contract_type, chain_name)
);

-- Smart Contract Transactions
CREATE TABLE IF NOT EXISTS smart_contract_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID REFERENCES smart_contracts(contract_id),
    transaction_hash VARCHAR(66) NOT NULL UNIQUE,
    function_name VARCHAR(100) NOT NULL,
    parameters JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    gas_used INTEGER,
    effective_gas_price BIGINT,
    block_number BIGINT,
    transaction_index INTEGER,
    logs JSONB,
    error_message TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    confirmed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- =============================================================================
-- FARM MANAGEMENT SYSTEM TABLES
-- =============================================================================

-- Farms
CREATE TABLE IF NOT EXISTS farms (
    farm_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farm_name VARCHAR(255) NOT NULL,
    farm_type VARCHAR(50) NOT NULL CHECK (farm_type IN ('trend_following', 'breakout', 'price_action', 'arbitrage', 'scalping', 'multi_strategy')),
    description TEXT,
    status VARCHAR(20) DEFAULT 'inactive' CHECK (status IN ('inactive', 'active', 'paused', 'maintenance', 'scaling')),
    max_agents INTEGER DEFAULT 10,
    current_agents INTEGER DEFAULT 0,
    assigned_agents UUID[] DEFAULT ARRAY[]::UUID[],
    strategy_config JSONB DEFAULT '{}'::jsonb,
    performance_target JSONB DEFAULT '{}'::jsonb,
    risk_limits JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Farm Agent Assignments
CREATE TABLE IF NOT EXISTS farm_agent_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farm_id UUID REFERENCES farms(farm_id) ON DELETE CASCADE,
    agent_id UUID NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    removed_at TIMESTAMP WITH TIME ZONE,
    role VARCHAR(50) DEFAULT 'primary' CHECK (role IN ('primary', 'support', 'specialist')),
    performance_weight DECIMAL(3,2) DEFAULT 1.0,
    is_active BOOLEAN DEFAULT true,
    assignment_metadata JSONB DEFAULT '{}'::jsonb
);

-- Farm Performance
CREATE TABLE IF NOT EXISTS farm_performance (
    performance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farm_id UUID REFERENCES farms(farm_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(),
    total_profit DECIMAL(20,2) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(4,3) DEFAULT 0,
    avg_profit_per_trade DECIMAL(20,2) DEFAULT 0,
    sharpe_ratio DECIMAL(8,4) DEFAULT 0,
    max_drawdown DECIMAL(4,3) DEFAULT 0,
    active_agents INTEGER DEFAULT 0,
    agent_coordination_score DECIMAL(4,3) DEFAULT 0,
    strategy_efficiency DECIMAL(4,3) DEFAULT 0,
    risk_adjusted_return DECIMAL(20,2) DEFAULT 0,
    performance_metadata JSONB DEFAULT '{}'::jsonb
);

-- =============================================================================
-- GOAL MANAGEMENT SYSTEM TABLES
-- =============================================================================

-- Goals
CREATE TABLE IF NOT EXISTS goals (
    goal_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_name VARCHAR(255) NOT NULL,
    goal_type VARCHAR(50) NOT NULL CHECK (goal_type IN ('profit_target', 'trade_count', 'win_rate', 'portfolio_value', 'risk_management', 'strategy_performance', 'time_based', 'collaborative')),
    description TEXT,
    target_value DECIMAL(20,2) NOT NULL,
    current_value DECIMAL(20,2) DEFAULT 0,
    progress_percentage DECIMAL(5,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'in_progress', 'completed', 'failed', 'cancelled', 'paused')),
    priority INTEGER DEFAULT 2 CHECK (priority BETWEEN 1 AND 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    target_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    assigned_agents UUID[] DEFAULT ARRAY[]::UUID[],
    assigned_farms UUID[] DEFAULT ARRAY[]::UUID[],
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Goal Progress
CREATE TABLE IF NOT EXISTS goal_progress (
    progress_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID REFERENCES goals(goal_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(),
    current_value DECIMAL(20,2) NOT NULL,
    progress_percentage DECIMAL(5,2) NOT NULL,
    velocity DECIMAL(10,4) DEFAULT 0, -- Progress per day
    estimated_completion TIMESTAMP WITH TIME ZONE,
    milestones_achieved TEXT[] DEFAULT ARRAY[]::TEXT[],
    blockers TEXT[] DEFAULT ARRAY[]::TEXT[],
    progress_metadata JSONB DEFAULT '{}'::jsonb
);

-- Goal Completions
CREATE TABLE IF NOT EXISTS goal_completions (
    completion_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID REFERENCES goals(goal_id) ON DELETE CASCADE,
    completion_timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(),
    final_value DECIMAL(20,2) NOT NULL,
    success_rate DECIMAL(4,3) DEFAULT 1.0,
    total_profit DECIMAL(20,2) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    completion_time_days INTEGER DEFAULT 0,
    contributing_agents UUID[] DEFAULT ARRAY[]::UUID[],
    contributing_farms UUID[] DEFAULT ARRAY[]::UUID[],
    performance_metrics JSONB DEFAULT '{}'::jsonb
);

-- =============================================================================
-- ALLOCATION & DISTRIBUTION TABLES
-- =============================================================================

-- Allocation History
CREATE TABLE IF NOT EXISTS allocation_history (
    history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_id UUID REFERENCES master_wallets(wallet_id) ON DELETE CASCADE,
    allocation_timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(),
    target_type VARCHAR(50) NOT NULL,
    target_id UUID NOT NULL,
    allocation_amount DECIMAL(20,2) NOT NULL,
    initial_performance_score DECIMAL(4,3),
    initial_risk_score DECIMAL(4,3),
    target_priority INTEGER,
    market_volatility DECIMAL(4,3),
    allocation_duration_days INTEGER,
    actual_performance DECIMAL(10,4),
    actual_risk DECIMAL(4,3),
    final_pnl DECIMAL(20,2),
    allocation_metadata JSONB DEFAULT '{}'::jsonb
);

-- Allocation Executions
CREATE TABLE IF NOT EXISTS allocation_executions (
    execution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_id UUID REFERENCES master_wallets(wallet_id) ON DELETE CASCADE,
    execution_timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(),
    recommendations_count INTEGER DEFAULT 0,
    successful_executions INTEGER DEFAULT 0,
    failed_executions INTEGER DEFAULT 0,
    total_allocated DECIMAL(20,2) DEFAULT 0,
    total_collected DECIMAL(20,2) DEFAULT 0,
    execution_details JSONB DEFAULT '{}'::jsonb
);

-- =============================================================================
-- ENHANCED AGENT TABLES (extending existing)
-- =============================================================================

-- Agent Goals (many-to-many relationship)
CREATE TABLE IF NOT EXISTS agent_goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL,
    goal_id UUID REFERENCES goals(goal_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    contribution_weight DECIMAL(4,3) DEFAULT 1.0,
    progress_contribution DECIMAL(20,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(agent_id, goal_id)
);

-- Agent Farm Coordination
CREATE TABLE IF NOT EXISTS agent_farm_coordination (
    coordination_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL,
    farm_id UUID REFERENCES farms(farm_id) ON DELETE CASCADE,
    coordination_start TIMESTAMP WITH TIME ZONE DEFAULT now(),
    coordination_score DECIMAL(4,3) DEFAULT 0.5,
    communication_frequency INTEGER DEFAULT 10, -- messages per hour
    collaboration_effectiveness DECIMAL(4,3) DEFAULT 0.5,
    last_coordination TIMESTAMP WITH TIME ZONE DEFAULT now(),
    is_coordinating BOOLEAN DEFAULT true
);

-- =============================================================================
-- AUTONOMOUS FUND DISTRIBUTION TABLES
-- =============================================================================

-- Distribution Recommendations
CREATE TABLE IF NOT EXISTS distribution_recommendations (
    recommendation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_id UUID REFERENCES master_wallets(wallet_id) ON DELETE CASCADE,
    target_id UUID NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    current_allocation DECIMAL(20,2) NOT NULL,
    recommended_allocation DECIMAL(20,2) NOT NULL,
    allocation_change DECIMAL(20,2) NOT NULL,
    confidence_score DECIMAL(4,3) NOT NULL,
    reasoning TEXT,
    risk_assessment TEXT,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    executed_at TIMESTAMP WITH TIME ZONE,
    execution_status VARCHAR(20) DEFAULT 'pending'
);

-- =============================================================================
-- SYSTEM MONITORING & HEALTH TABLES
-- =============================================================================

-- Service Health
CREATE TABLE IF NOT EXISTS service_health (
    health_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'unknown',
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT now(),
    response_time_ms INTEGER,
    error_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    health_metrics JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(service_name)
);

-- System Events
CREATE TABLE IF NOT EXISTS system_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    event_source VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    severity VARCHAR(20) DEFAULT 'info' CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    processed_at TIMESTAMP WITH TIME ZONE,
    is_processed BOOLEAN DEFAULT false
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Master Wallet Indexes
CREATE INDEX IF NOT EXISTS idx_master_wallets_active ON master_wallets(is_active);
CREATE INDEX IF NOT EXISTS idx_wallet_addresses_wallet_id ON wallet_addresses(wallet_id);
CREATE INDEX IF NOT EXISTS idx_wallet_balances_wallet_id ON wallet_balances(wallet_id);
CREATE INDEX IF NOT EXISTS idx_fund_allocations_wallet_id ON fund_allocations(wallet_id);
CREATE INDEX IF NOT EXISTS idx_fund_allocations_target ON fund_allocations(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_fund_allocations_active ON fund_allocations(is_active);

-- Farm Indexes
CREATE INDEX IF NOT EXISTS idx_farms_status ON farms(status);
CREATE INDEX IF NOT EXISTS idx_farms_type ON farms(farm_type);
CREATE INDEX IF NOT EXISTS idx_farm_assignments_farm_id ON farm_agent_assignments(farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_assignments_agent_id ON farm_agent_assignments(agent_id);
CREATE INDEX IF NOT EXISTS idx_farm_assignments_active ON farm_agent_assignments(is_active);
CREATE INDEX IF NOT EXISTS idx_farm_performance_farm_id ON farm_performance(farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_performance_timestamp ON farm_performance(timestamp);

-- Goal Indexes
CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
CREATE INDEX IF NOT EXISTS idx_goals_type ON goals(goal_type);
CREATE INDEX IF NOT EXISTS idx_goals_priority ON goals(priority);
CREATE INDEX IF NOT EXISTS idx_goals_target_date ON goals(target_date);
CREATE INDEX IF NOT EXISTS idx_goal_progress_goal_id ON goal_progress(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_progress_timestamp ON goal_progress(timestamp);
CREATE INDEX IF NOT EXISTS idx_goal_completions_goal_id ON goal_completions(goal_id);

-- Agent Indexes
CREATE INDEX IF NOT EXISTS idx_agent_goals_agent_id ON agent_goals(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_goals_goal_id ON agent_goals(goal_id);
CREATE INDEX IF NOT EXISTS idx_agent_goals_active ON agent_goals(is_active);
CREATE INDEX IF NOT EXISTS idx_agent_coordination_agent_id ON agent_farm_coordination(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_coordination_farm_id ON agent_farm_coordination(farm_id);

-- Transaction Indexes
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_wallet_id ON wallet_transactions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_type ON wallet_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_status ON wallet_transactions(status);
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_created_at ON wallet_transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_smart_contract_transactions_hash ON smart_contract_transactions(transaction_hash);
CREATE INDEX IF NOT EXISTS idx_smart_contract_transactions_status ON smart_contract_transactions(status);

-- System Indexes
CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events(event_type);
CREATE INDEX IF NOT EXISTS idx_system_events_source ON system_events(event_source);
CREATE INDEX IF NOT EXISTS idx_system_events_created_at ON system_events(created_at);
CREATE INDEX IF NOT EXISTS idx_system_events_processed ON system_events(is_processed);
CREATE INDEX IF NOT EXISTS idx_service_health_service ON service_health(service_name);

-- =============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- =============================================================================

-- Function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers to relevant tables
CREATE TRIGGER update_master_wallets_updated_at BEFORE UPDATE ON master_wallets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_farms_updated_at BEFORE UPDATE ON farms
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_goals_updated_at BEFORE UPDATE ON goals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fund_distribution_rules_updated_at BEFORE UPDATE ON fund_distribution_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_service_health_updated_at BEFORE UPDATE ON service_health
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================================================

-- Enable RLS on sensitive tables
ALTER TABLE master_wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallet_addresses ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallet_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE fund_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE smart_contracts ENABLE ROW LEVEL SECURITY;

-- Example RLS policies (customize based on your auth system)
CREATE POLICY "Users can view their own wallets" ON master_wallets
    FOR SELECT USING (auth.uid() IS NOT NULL);

CREATE POLICY "Service role can manage all wallets" ON master_wallets
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- =============================================================================
-- FUNCTIONS FOR BUSINESS LOGIC
-- =============================================================================

-- Function to calculate goal progress
CREATE OR REPLACE FUNCTION calculate_goal_progress(goal_uuid UUID)
RETURNS DECIMAL AS $$
DECLARE
    goal_record RECORD;
    progress_percentage DECIMAL;
BEGIN
    SELECT target_value, current_value INTO goal_record FROM goals WHERE goal_id = goal_uuid;
    
    IF goal_record.target_value > 0 THEN
        progress_percentage := (goal_record.current_value / goal_record.target_value) * 100;
        progress_percentage := LEAST(progress_percentage, 100);
    ELSE
        progress_percentage := 0;
    END IF;
    
    RETURN progress_percentage;
END;
$$ LANGUAGE plpgsql;

-- Function to get farm performance summary
CREATE OR REPLACE FUNCTION get_farm_performance_summary(farm_uuid UUID, days_back INTEGER DEFAULT 30)
RETURNS TABLE(
    total_profit DECIMAL,
    total_trades INTEGER,
    avg_win_rate DECIMAL,
    avg_sharpe_ratio DECIMAL,
    latest_performance TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        SUM(fp.total_profit) as total_profit,
        SUM(fp.total_trades) as total_trades,
        AVG(fp.win_rate) as avg_win_rate,
        AVG(fp.sharpe_ratio) as avg_sharpe_ratio,
        MAX(fp.timestamp) as latest_performance
    FROM farm_performance fp
    WHERE fp.farm_id = farm_uuid 
        AND fp.timestamp >= (now() - INTERVAL '1 day' * days_back);
END;
$$ LANGUAGE plpgsql;

-- Function to check allocation limits
CREATE OR REPLACE FUNCTION check_allocation_limits(wallet_uuid UUID, allocation_amount DECIMAL)
RETURNS BOOLEAN AS $$
DECLARE
    wallet_record RECORD;
    current_allocations DECIMAL;
    max_allowed DECIMAL;
BEGIN
    -- Get wallet settings
    SELECT max_allocation_per_agent INTO wallet_record FROM master_wallets WHERE wallet_id = wallet_uuid;
    
    -- Calculate current total allocations
    SELECT COALESCE(SUM(current_value_usd), 0) INTO current_allocations 
    FROM fund_allocations 
    WHERE wallet_id = wallet_uuid AND is_active = true;
    
    -- Calculate maximum allowed allocation
    SELECT SUM(balance_usd) * wallet_record.max_allocation_per_agent INTO max_allowed
    FROM wallet_balances 
    WHERE wallet_id = wallet_uuid;
    
    -- Check if new allocation would exceed limits
    RETURN (current_allocations + allocation_amount) <= max_allowed;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- =============================================================================

-- Wallet summary view
CREATE MATERIALIZED VIEW IF NOT EXISTS wallet_summary AS
SELECT 
    mw.wallet_id,
    mw.wallet_name,
    mw.is_active,
    COALESCE(SUM(wb.balance_usd), 0) as total_balance_usd,
    COALESCE(SUM(fa.current_value_usd), 0) as total_allocated_usd,
    COALESCE(SUM(wb.balance_usd), 0) - COALESCE(SUM(fa.current_value_usd), 0) as available_balance_usd,
    COUNT(DISTINCT fa.allocation_id) as active_allocations,
    mw.updated_at
FROM master_wallets mw
LEFT JOIN wallet_balances wb ON mw.wallet_id = wb.wallet_id
LEFT JOIN fund_allocations fa ON mw.wallet_id = fa.wallet_id AND fa.is_active = true
GROUP BY mw.wallet_id, mw.wallet_name, mw.is_active, mw.updated_at;

-- Farm summary view
CREATE MATERIALIZED VIEW IF NOT EXISTS farm_summary AS
SELECT 
    f.farm_id,
    f.farm_name,
    f.farm_type,
    f.status,
    f.current_agents,
    f.max_agents,
    COALESCE(fp_latest.total_profit, 0) as latest_profit,
    COALESCE(fp_latest.total_trades, 0) as latest_trades,
    COALESCE(fp_latest.win_rate, 0) as latest_win_rate,
    f.updated_at
FROM farms f
LEFT JOIN LATERAL (
    SELECT total_profit, total_trades, win_rate
    FROM farm_performance 
    WHERE farm_id = f.farm_id 
    ORDER BY timestamp DESC 
    LIMIT 1
) fp_latest ON true;

-- Goal summary view
CREATE MATERIALIZED VIEW IF NOT EXISTS goal_summary AS
SELECT 
    g.goal_id,
    g.goal_name,
    g.goal_type,
    g.status,
    g.progress_percentage,
    g.target_value,
    g.current_value,
    ARRAY_LENGTH(g.assigned_agents, 1) as assigned_agent_count,
    ARRAY_LENGTH(g.assigned_farms, 1) as assigned_farm_count,
    g.target_date,
    g.updated_at
FROM goals g;

-- Refresh materialized views (should be done periodically)
CREATE OR REPLACE FUNCTION refresh_summary_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW wallet_summary;
    REFRESH MATERIALIZED VIEW farm_summary;
    REFRESH MATERIALIZED VIEW goal_summary;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- SAMPLE DATA INSERTION (for testing)
-- =============================================================================

-- Insert sample master wallet
INSERT INTO master_wallets (wallet_name, description, auto_distribution, max_allocation_per_agent)
VALUES ('Primary Trading Wallet', 'Main wallet for autonomous trading operations', true, 0.25)
ON CONFLICT DO NOTHING;

-- Insert sample farm templates
INSERT INTO farms (farm_name, farm_type, description, max_agents, strategy_config, performance_target)
VALUES 
('Trend Following Farm Alpha', 'trend_following', 'Primary trend following strategy farm', 15, 
 '{"primary_strategies": ["williams_alligator", "elliott_wave"], "timeframes": ["1h", "4h", "1d"], "risk_per_trade": 0.02}'::jsonb,
 '{"monthly_return": 0.08, "sharpe_ratio": 1.5, "max_drawdown": 0.1}'::jsonb),
('Breakout Strategy Farm Beta', 'breakout', 'High-frequency breakout trading farm', 12,
 '{"primary_strategies": ["darvas_box", "renko"], "volatility_threshold": 0.02, "volume_confirmation": true}'::jsonb,
 '{"monthly_return": 0.1, "win_rate": 0.6, "max_drawdown": 0.15}'::jsonb)
ON CONFLICT DO NOTHING;

-- Insert sample goals
INSERT INTO goals (goal_name, goal_type, description, target_value, priority)
VALUES 
('Daily Profit Target', 'profit_target', 'Achieve $50 profit in a single trading day', 50.00, 3),
('Weekly Trade Volume', 'trade_count', 'Execute 100 trades within one week', 100, 2),
('Monthly Win Rate Goal', 'win_rate', 'Maintain 70% win rate for the entire month', 0.70, 4)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- CLEANUP AND MAINTENANCE FUNCTIONS
-- =============================================================================

-- Function to cleanup old records
CREATE OR REPLACE FUNCTION cleanup_old_records()
RETURNS void AS $$
BEGIN
    -- Delete old goal progress records (keep last 30 days)
    DELETE FROM goal_progress WHERE timestamp < (now() - INTERVAL '30 days');
    
    -- Delete old farm performance records (keep last 90 days)
    DELETE FROM farm_performance WHERE timestamp < (now() - INTERVAL '90 days');
    
    -- Delete old system events (keep last 7 days)
    DELETE FROM system_events WHERE created_at < (now() - INTERVAL '7 days') AND is_processed = true;
    
    -- Delete old wallet transactions (keep last 180 days)
    DELETE FROM wallet_transactions WHERE created_at < (now() - INTERVAL '180 days') AND status = 'confirmed';
    
    -- Refresh materialized views
    PERFORM refresh_summary_views();
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- GRANTS AND PERMISSIONS
-- =============================================================================

-- Grant necessary permissions to service role
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO service_role;

-- Grant read permissions to authenticated users
GRANT SELECT ON wallet_summary TO authenticated;
GRANT SELECT ON farm_summary TO authenticated;
GRANT SELECT ON goal_summary TO authenticated;

-- =============================================================================
-- FINAL NOTES
-- =============================================================================

-- This schema provides:
-- 1. Complete master wallet system with multi-chain support
-- 2. Advanced farm management for agent coordination
-- 3. Comprehensive goal system with autonomous completion
-- 4. Smart contract integration for on-chain operations
-- 5. Autonomous fund distribution with AI-powered allocation
-- 6. Performance monitoring and analytics
-- 7. Proper indexing for high-performance queries
-- 8. Row-level security for data protection
-- 9. Materialized views for dashboard performance
-- 10. Maintenance functions for long-term operations

-- Remember to:
-- 1. Set up proper backup strategies
-- 2. Monitor query performance and adjust indexes
-- 3. Run cleanup functions periodically
-- 4. Update RLS policies based on your authentication system
-- 5. Refresh materialized views on a schedule (every 5-15 minutes)

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================