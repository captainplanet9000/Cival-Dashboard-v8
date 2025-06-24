-- Farms Management Database Schema
-- Comprehensive schema for trading farm coordination and management

-- Farms table - Core farm definitions
CREATE TABLE IF NOT EXISTS farms (
    farm_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    farm_type VARCHAR(50) NOT NULL DEFAULT 'trading' CHECK (farm_type IN (
        'trading', 'arbitrage', 'market_making', 'defi', 'research', 'risk_management'
    )),
    strategy VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'inactive' CHECK (status IN (
        'inactive', 'active', 'paused', 'error', 'maintenance', 'scaling'
    )),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    paused_at TIMESTAMP WITH TIME ZONE,
    
    -- Financial metrics
    initial_capital DECIMAL(15,2) DEFAULT 0,
    current_capital DECIMAL(15,2) DEFAULT 0,
    total_pnl DECIMAL(15,2) DEFAULT 0,
    daily_pnl DECIMAL(15,2) DEFAULT 0,
    unrealized_pnl DECIMAL(15,2) DEFAULT 0,
    realized_pnl DECIMAL(15,2) DEFAULT 0,
    
    -- Configuration
    max_agents INTEGER DEFAULT 10,
    current_agents INTEGER DEFAULT 0,
    target_allocation DECIMAL(15,2) DEFAULT 0,
    risk_limit DECIMAL(5,4) DEFAULT 0.05,
    
    -- Performance thresholds
    min_performance_score DECIMAL(3,2) DEFAULT 0.50,
    auto_scale_enabled BOOLEAN DEFAULT FALSE,
    auto_rebalance_enabled BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    configuration JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT positive_capital CHECK (initial_capital >= 0 AND current_capital >= 0),
    CONSTRAINT valid_agents CHECK (current_agents >= 0 AND current_agents <= max_agents),
    CONSTRAINT valid_risk_limit CHECK (risk_limit >= 0 AND risk_limit <= 1)
);

-- Farm agents - Agents assigned to farms
CREATE TABLE IF NOT EXISTS farm_agents (
    assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    agent_id VARCHAR(255) NOT NULL,
    agent_name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    
    -- Assignment details
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    removed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN (
        'active', 'paused', 'error', 'training', 'removed'
    )),
    role VARCHAR(50) DEFAULT 'trader' CHECK (role IN (
        'trader', 'coordinator', 'risk_manager', 'researcher', 'specialist'
    )),
    
    -- Performance tracking
    allocation DECIMAL(15,2) DEFAULT 0,
    current_pnl DECIMAL(15,2) DEFAULT 0,
    daily_pnl DECIMAL(15,2) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5,4) DEFAULT 0,
    
    -- Activity tracking
    last_activity TIMESTAMP WITH TIME ZONE,
    last_trade TIMESTAMP WITH TIME ZONE,
    last_decision TIMESTAMP WITH TIME ZONE,
    
    -- Performance metrics
    sharpe_ratio DECIMAL(6,4) DEFAULT 0,
    max_drawdown DECIMAL(5,4) DEFAULT 0,
    avg_trade_size DECIMAL(15,2) DEFAULT 0,
    performance_score DECIMAL(3,2) DEFAULT 0.50,
    
    -- Configuration
    agent_config JSONB DEFAULT '{}'::jsonb,
    
    -- Unique constraint
    UNIQUE(farm_id, agent_id)
);

-- Farm performance - Historical performance tracking
CREATE TABLE IF NOT EXISTS farm_performance (
    performance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    date DATE DEFAULT CURRENT_DATE,
    
    -- Financial metrics
    total_capital DECIMAL(15,2) NOT NULL,
    total_pnl DECIMAL(15,2) DEFAULT 0,
    daily_pnl DECIMAL(15,2) DEFAULT 0,
    unrealized_pnl DECIMAL(15,2) DEFAULT 0,
    realized_pnl DECIMAL(15,2) DEFAULT 0,
    
    -- Trading metrics
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5,4) DEFAULT 0,
    avg_trade_size DECIMAL(15,2) DEFAULT 0,
    
    -- Risk metrics
    sharpe_ratio DECIMAL(6,4) DEFAULT 0,
    max_drawdown DECIMAL(5,4) DEFAULT 0,
    volatility DECIMAL(6,4) DEFAULT 0,
    var_95 DECIMAL(15,2) DEFAULT 0,
    
    -- Farm-specific metrics
    agent_count INTEGER DEFAULT 0,
    active_agent_count INTEGER DEFAULT 0,
    coordination_score DECIMAL(3,2) DEFAULT 0.50,
    strategy_efficiency DECIMAL(3,2) DEFAULT 0.50,
    
    -- System metrics
    system_load DECIMAL(3,2) DEFAULT 0,
    network_latency DECIMAL(6,2) DEFAULT 0,
    processing_speed DECIMAL(8,2) DEFAULT 0,
    error_rate DECIMAL(5,4) DEFAULT 0,
    
    -- Unique constraint for daily snapshots
    UNIQUE(farm_id, date)
);

-- Farm targets - Performance targets and goals
CREATE TABLE IF NOT EXISTS farm_targets (
    target_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    target_type VARCHAR(50) NOT NULL CHECK (target_type IN (
        'daily_profit', 'monthly_profit', 'win_rate', 'sharpe_ratio', 
        'max_drawdown', 'trade_volume', 'capital_efficiency'
    )),
    target_value DECIMAL(15,4) NOT NULL,
    current_value DECIMAL(15,4) DEFAULT 0,
    target_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    achieved_at TIMESTAMP WITH TIME ZONE,
    is_achieved BOOLEAN DEFAULT FALSE,
    progress_percentage DECIMAL(5,2) DEFAULT 0,
    
    -- Metadata
    description TEXT,
    priority INTEGER DEFAULT 2 CHECK (priority >= 1 AND priority <= 5),
    auto_adjust BOOLEAN DEFAULT FALSE,
    
    -- Constraints
    CONSTRAINT valid_progress CHECK (progress_percentage >= 0 AND progress_percentage <= 100)
);

-- Farm risk metrics - Real-time risk monitoring
CREATE TABLE IF NOT EXISTS farm_risk_metrics (
    risk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Exposure metrics
    current_exposure DECIMAL(15,2) DEFAULT 0,
    max_exposure DECIMAL(15,2) DEFAULT 0,
    exposure_ratio DECIMAL(5,4) DEFAULT 0,
    
    -- Diversification metrics
    diversification_score DECIMAL(3,2) DEFAULT 0.50,
    correlation_risk DECIMAL(5,4) DEFAULT 0,
    concentration_risk DECIMAL(5,4) DEFAULT 0,
    
    -- Volatility metrics
    portfolio_volatility DECIMAL(6,4) DEFAULT 0,
    var_1d DECIMAL(15,2) DEFAULT 0,
    var_1w DECIMAL(15,2) DEFAULT 0,
    expected_shortfall DECIMAL(15,2) DEFAULT 0,
    
    -- Liquidity metrics
    liquidity_score DECIMAL(3,2) DEFAULT 0.50,
    liquidation_time_estimate INTEGER DEFAULT 0, -- minutes
    
    -- Risk limits and violations
    risk_limits JSONB DEFAULT '{}'::jsonb,
    current_violations TEXT[] DEFAULT '{}',
    violation_count INTEGER DEFAULT 0,
    
    -- Risk assessment
    overall_risk_score DECIMAL(3,2) DEFAULT 0.50,
    risk_level VARCHAR(10) DEFAULT 'medium' CHECK (risk_level IN ('low', 'medium', 'high', 'critical'))
);

-- Farm orders - Order management and tracking
CREATE TABLE IF NOT EXISTS farm_orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    agent_id VARCHAR(255),
    
    -- Order details
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL CHECK (side IN ('buy', 'sell')),
    order_type VARCHAR(20) NOT NULL CHECK (order_type IN (
        'market', 'limit', 'stop', 'stop_limit', 'trailing_stop'
    )),
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8),
    stop_price DECIMAL(20,8),
    
    -- Status and timing
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'submitted', 'filled', 'partially_filled', 
        'cancelled', 'rejected', 'expired'
    )),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    submitted_at TIMESTAMP WITH TIME ZONE,
    filled_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    
    -- Execution details
    filled_quantity DECIMAL(20,8) DEFAULT 0,
    average_fill_price DECIMAL(20,8) DEFAULT 0,
    commission DECIMAL(15,8) DEFAULT 0,
    total_cost DECIMAL(15,2) DEFAULT 0,
    
    -- External references
    exchange_id VARCHAR(100),
    exchange_order_id VARCHAR(255),
    
    -- Metadata
    strategy VARCHAR(100),
    reasoning TEXT,
    order_metadata JSONB DEFAULT '{}'::jsonb
);

-- Farm communications - Inter-farm and agent communication
CREATE TABLE IF NOT EXISTS farm_communications (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    
    -- Message details
    message_type VARCHAR(50) NOT NULL CHECK (message_type IN (
        'coordination', 'alert', 'decision', 'performance', 'risk', 'system'
    )),
    sender_type VARCHAR(20) NOT NULL CHECK (sender_type IN ('farm', 'agent', 'system')),
    sender_id VARCHAR(255) NOT NULL,
    recipient_type VARCHAR(20) CHECK (recipient_type IN ('farm', 'agent', 'broadcast')),
    recipient_id VARCHAR(255),
    
    -- Content
    subject VARCHAR(255),
    content TEXT NOT NULL,
    priority VARCHAR(10) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    
    -- Status
    status VARCHAR(20) DEFAULT 'sent' CHECK (status IN ('draft', 'sent', 'delivered', 'read', 'processed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    response_to UUID REFERENCES farm_communications(message_id)
);

-- Farm events - Comprehensive event logging
CREATE TABLE IF NOT EXISTS farm_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    agent_id VARCHAR(255),
    
    -- Event details
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(30) NOT NULL CHECK (event_category IN (
        'system', 'trading', 'performance', 'risk', 'communication', 'error'
    )),
    event_data JSONB NOT NULL,
    
    -- Timing and status
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_status VARCHAR(20) DEFAULT 'pending' CHECK (processing_status IN (
        'pending', 'processing', 'completed', 'failed', 'ignored'
    )),
    
    -- Context
    triggered_by VARCHAR(255),
    impact_level VARCHAR(10) DEFAULT 'low' CHECK (impact_level IN ('low', 'medium', 'high', 'critical')),
    
    -- Response tracking
    response_required BOOLEAN DEFAULT FALSE,
    response_deadline TIMESTAMP WITH TIME ZONE,
    responded_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_farms_status ON farms(status);
CREATE INDEX IF NOT EXISTS idx_farms_type ON farms(farm_type);
CREATE INDEX IF NOT EXISTS idx_farms_created_at ON farms(created_at);

CREATE INDEX IF NOT EXISTS idx_farm_agents_farm_id ON farm_agents(farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_agents_agent_id ON farm_agents(agent_id);
CREATE INDEX IF NOT EXISTS idx_farm_agents_status ON farm_agents(status);
CREATE INDEX IF NOT EXISTS idx_farm_agents_performance ON farm_agents(performance_score);

CREATE INDEX IF NOT EXISTS idx_farm_performance_farm_id ON farm_performance(farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_performance_date ON farm_performance(date);
CREATE INDEX IF NOT EXISTS idx_farm_performance_timestamp ON farm_performance(timestamp);

CREATE INDEX IF NOT EXISTS idx_farm_targets_farm_id ON farm_targets(farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_targets_type ON farm_targets(target_type);
CREATE INDEX IF NOT EXISTS idx_farm_targets_achieved ON farm_targets(is_achieved);

CREATE INDEX IF NOT EXISTS idx_farm_risk_farm_id ON farm_risk_metrics(farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_risk_timestamp ON farm_risk_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_farm_risk_level ON farm_risk_metrics(risk_level);

CREATE INDEX IF NOT EXISTS idx_farm_orders_farm_id ON farm_orders(farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_orders_agent_id ON farm_orders(agent_id);
CREATE INDEX IF NOT EXISTS idx_farm_orders_status ON farm_orders(status);
CREATE INDEX IF NOT EXISTS idx_farm_orders_symbol ON farm_orders(symbol);
CREATE INDEX IF NOT EXISTS idx_farm_orders_created_at ON farm_orders(created_at);

CREATE INDEX IF NOT EXISTS idx_farm_communications_farm_id ON farm_communications(farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_communications_type ON farm_communications(message_type);
CREATE INDEX IF NOT EXISTS idx_farm_communications_status ON farm_communications(status);
CREATE INDEX IF NOT EXISTS idx_farm_communications_created_at ON farm_communications(created_at);

CREATE INDEX IF NOT EXISTS idx_farm_events_farm_id ON farm_events(farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_events_agent_id ON farm_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_farm_events_type ON farm_events(event_type);
CREATE INDEX IF NOT EXISTS idx_farm_events_category ON farm_events(event_category);
CREATE INDEX IF NOT EXISTS idx_farm_events_timestamp ON farm_events(timestamp);

-- Triggers for automatic updates
CREATE OR REPLACE FUNCTION update_farm_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_farms_updated_at 
    BEFORE UPDATE ON farms 
    FOR EACH ROW 
    EXECUTE FUNCTION update_farm_updated_at();

-- Function to update farm agent counts
CREATE OR REPLACE FUNCTION update_farm_agent_count()
RETURNS TRIGGER AS $$
BEGIN
    -- Update current_agents count in farms table
    UPDATE farms 
    SET current_agents = (
        SELECT COUNT(*) 
        FROM farm_agents 
        WHERE farm_id = COALESCE(NEW.farm_id, OLD.farm_id)
        AND status = 'active'
    )
    WHERE farm_id = COALESCE(NEW.farm_id, OLD.farm_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_farm_agent_count_insert 
    AFTER INSERT ON farm_agents 
    FOR EACH ROW 
    EXECUTE FUNCTION update_farm_agent_count();

CREATE TRIGGER trigger_update_farm_agent_count_update 
    AFTER UPDATE ON farm_agents 
    FOR EACH ROW 
    EXECUTE FUNCTION update_farm_agent_count();

CREATE TRIGGER trigger_update_farm_agent_count_delete 
    AFTER DELETE ON farm_agents 
    FOR EACH ROW 
    EXECUTE FUNCTION update_farm_agent_count();

-- Function to calculate win rates
CREATE OR REPLACE FUNCTION update_win_rates()
RETURNS TRIGGER AS $$
BEGIN
    -- Update win rate for the agent
    UPDATE farm_agents 
    SET win_rate = CASE 
        WHEN (winning_trades + losing_trades) > 0 
        THEN winning_trades::DECIMAL / (winning_trades + losing_trades)
        ELSE 0 
    END
    WHERE farm_id = NEW.farm_id AND agent_id = NEW.agent_id;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_win_rates 
    AFTER UPDATE OF winning_trades, losing_trades ON farm_agents 
    FOR EACH ROW 
    EXECUTE FUNCTION update_win_rates();

-- Function to automatically update target progress
CREATE OR REPLACE FUNCTION update_target_progress()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate progress percentage
    NEW.progress_percentage = CASE 
        WHEN NEW.target_value > 0 
        THEN LEAST(100.0, (NEW.current_value / NEW.target_value * 100))
        ELSE 0 
    END;
    
    -- Check if target is achieved
    IF NEW.progress_percentage >= 100 AND NOT NEW.is_achieved THEN
        NEW.is_achieved = TRUE;
        NEW.achieved_at = NOW();
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_target_progress 
    BEFORE UPDATE OF current_value ON farm_targets 
    FOR EACH ROW 
    EXECUTE FUNCTION update_target_progress();

-- Row Level Security (RLS) policies
ALTER TABLE farms ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_risk_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_communications ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_events ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies
CREATE POLICY "Allow all operations on farms" ON farms FOR ALL USING (true);
CREATE POLICY "Allow all operations on farm_agents" ON farm_agents FOR ALL USING (true);
CREATE POLICY "Allow all operations on farm_performance" ON farm_performance FOR ALL USING (true);
CREATE POLICY "Allow all operations on farm_targets" ON farm_targets FOR ALL USING (true);
CREATE POLICY "Allow all operations on farm_risk_metrics" ON farm_risk_metrics FOR ALL USING (true);
CREATE POLICY "Allow all operations on farm_orders" ON farm_orders FOR ALL USING (true);
CREATE POLICY "Allow all operations on farm_communications" ON farm_communications FOR ALL USING (true);
CREATE POLICY "Allow all operations on farm_events" ON farm_events FOR ALL USING (true);

-- Comments for documentation
COMMENT ON TABLE farms IS 'Core farms table for managing trading farm coordination';
COMMENT ON TABLE farm_agents IS 'Agents assigned to farms with performance tracking';
COMMENT ON TABLE farm_performance IS 'Historical performance metrics for farms';
COMMENT ON TABLE farm_targets IS 'Performance targets and achievement tracking';
COMMENT ON TABLE farm_risk_metrics IS 'Real-time risk monitoring and assessment';
COMMENT ON TABLE farm_orders IS 'Order management and execution tracking';
COMMENT ON TABLE farm_communications IS 'Inter-farm and agent communication system';
COMMENT ON TABLE farm_events IS 'Comprehensive event logging and audit trail';