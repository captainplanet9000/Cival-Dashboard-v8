-- =====================================================
-- Supabase Migration: Wallet-Farm-Goal Integration
-- Version: 001
-- Description: Complete database schema for wallet hierarchy, farm management, and goal system
-- =====================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- FARM MANAGEMENT TABLES
-- =====================================================

-- Main farms table
CREATE TABLE IF NOT EXISTS farms (
    farm_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    farm_type VARCHAR(100) NOT NULL, -- 'trend_following', 'breakout', 'price_action'
    configuration JSONB NOT NULL DEFAULT '{}',
    wallet_address VARCHAR(255),
    total_allocated_usd DECIMAL(20,8) DEFAULT 0,
    performance_metrics JSONB DEFAULT '{}',
    risk_metrics JSONB DEFAULT '{}',
    agent_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT farms_name_unique UNIQUE(name),
    CONSTRAINT farms_farm_type_check CHECK (farm_type IN ('trend_following', 'breakout', 'price_action', 'mixed_strategy', 'custom')),
    CONSTRAINT farms_total_allocated_positive CHECK (total_allocated_usd >= 0)
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_farms_farm_type ON farms(farm_type);
CREATE INDEX IF NOT EXISTS idx_farms_is_active ON farms(is_active);
CREATE INDEX IF NOT EXISTS idx_farms_created_at ON farms(created_at);

-- =====================================================
-- GOAL MANAGEMENT TABLES
-- =====================================================

-- Main goals table
CREATE TABLE IF NOT EXISTS goals (
    goal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    goal_type VARCHAR(100) NOT NULL, -- 'trade_volume', 'profit_target', 'strategy_performance'
    target_criteria JSONB NOT NULL, -- {"trades": 200, "profit_per_trade": 5}
    current_progress JSONB DEFAULT '{}',
    assigned_entities JSONB DEFAULT '[]', -- [{"type": "farm", "id": "..."}, {"type": "agent", "id": "..."}]
    completion_status VARCHAR(50) DEFAULT 'active', -- 'active', 'completed', 'failed', 'paused'
    completion_percentage DECIMAL(5,2) DEFAULT 0,
    wallet_allocation_usd DECIMAL(20,8) DEFAULT 0,
    priority INTEGER DEFAULT 1, -- 1-10 priority scale
    deadline TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT goals_name_unique UNIQUE(name),
    CONSTRAINT goals_completion_status_check CHECK (completion_status IN ('active', 'completed', 'failed', 'paused')),
    CONSTRAINT goals_completion_percentage_check CHECK (completion_percentage >= 0 AND completion_percentage <= 100),
    CONSTRAINT goals_priority_check CHECK (priority >= 1 AND priority <= 10),
    CONSTRAINT goals_wallet_allocation_positive CHECK (wallet_allocation_usd >= 0)
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_goals_goal_type ON goals(goal_type);
CREATE INDEX IF NOT EXISTS idx_goals_completion_status ON goals(completion_status);
CREATE INDEX IF NOT EXISTS idx_goals_priority ON goals(priority);
CREATE INDEX IF NOT EXISTS idx_goals_deadline ON goals(deadline);

-- =====================================================
-- MASTER WALLET TABLES
-- =====================================================

-- Main master wallets table
CREATE TABLE IF NOT EXISTS master_wallets (
    wallet_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    configuration JSONB NOT NULL DEFAULT '{}',
    addresses JSONB DEFAULT '[]', -- Multi-chain addresses
    balances JSONB DEFAULT '{}', -- Current balances by asset
    total_value_usd DECIMAL(20,8) DEFAULT 0,
    performance_metrics JSONB DEFAULT '{}',
    risk_settings JSONB DEFAULT '{}',
    auto_distribution_enabled BOOLEAN DEFAULT true,
    emergency_stop_enabled BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT master_wallets_name_unique UNIQUE(name),
    CONSTRAINT master_wallets_total_value_positive CHECK (total_value_usd >= 0)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_master_wallets_is_active ON master_wallets(is_active);
CREATE INDEX IF NOT EXISTS idx_master_wallets_total_value ON master_wallets(total_value_usd);

-- =====================================================
-- FUND ALLOCATION TABLES
-- =====================================================

-- Fund allocations table
CREATE TABLE IF NOT EXISTS fund_allocations (
    allocation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID NOT NULL,
    target_type VARCHAR(50) NOT NULL, -- 'agent', 'farm', 'goal'
    target_id UUID NOT NULL,
    target_name VARCHAR(255),
    allocated_amount_usd DECIMAL(20,8) NOT NULL,
    allocated_percentage DECIMAL(5,2),
    current_value_usd DECIMAL(20,8),
    initial_allocation_usd DECIMAL(20,8),
    total_pnl DECIMAL(20,8) DEFAULT 0,
    unrealized_pnl DECIMAL(20,8) DEFAULT 0,
    realized_pnl DECIMAL(20,8) DEFAULT 0,
    performance_metrics JSONB DEFAULT '{}',
    allocation_method VARCHAR(100), -- 'manual', 'performance_based', 'equal_weight'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fund_allocations_target_type_check CHECK (target_type IN ('agent', 'farm', 'goal')),
    CONSTRAINT fund_allocations_allocated_amount_positive CHECK (allocated_amount_usd >= 0),
    CONSTRAINT fund_allocations_allocation_percentage_check CHECK (allocated_percentage >= 0 AND allocated_percentage <= 100)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_fund_allocations_wallet_id ON fund_allocations(wallet_id);
CREATE INDEX IF NOT EXISTS idx_fund_allocations_target_type ON fund_allocations(target_type);
CREATE INDEX IF NOT EXISTS idx_fund_allocations_target_id ON fund_allocations(target_id);
CREATE INDEX IF NOT EXISTS idx_fund_allocations_is_active ON fund_allocations(is_active);

-- =====================================================
-- WALLET TRANSACTIONS TABLE
-- =====================================================

-- Wallet transactions table
CREATE TABLE IF NOT EXISTS wallet_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID,
    transaction_type VARCHAR(100) NOT NULL,
    amount DECIMAL(20,8) NOT NULL,
    asset_symbol VARCHAR(20),
    amount_usd DECIMAL(20,8),
    from_entity VARCHAR(255),
    to_entity VARCHAR(255),
    from_address VARCHAR(255),
    to_address VARCHAR(255),
    blockchain_data JSONB DEFAULT '{}', -- tx_hash, block_number, gas_used, etc.
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confirmed_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT wallet_transactions_status_check CHECK (status IN ('pending', 'confirmed', 'failed', 'cancelled')),
    CONSTRAINT wallet_transactions_transaction_type_check CHECK (transaction_type IN ('deposit', 'withdrawal', 'allocation', 'collection', 'transfer', 'fee', 'reward'))
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_wallet_id ON wallet_transactions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_transaction_type ON wallet_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_status ON wallet_transactions(status);
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_created_at ON wallet_transactions(created_at);

-- =====================================================
-- RELATIONSHIP TABLES
-- =====================================================

-- Agent-Farm assignments table
CREATE TABLE IF NOT EXISTS agent_farm_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    farm_id UUID NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    role VARCHAR(100), -- 'primary', 'secondary', 'specialist', 'coordinator'
    allocated_funds_usd DECIMAL(20,8) DEFAULT 0,
    performance_contribution JSONB DEFAULT '{}',
    assignment_weight DECIMAL(3,2) DEFAULT 1.0, -- How much this agent contributes to farm
    is_active BOOLEAN DEFAULT true,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT agent_farm_assignments_unique UNIQUE(agent_id, farm_id),
    CONSTRAINT agent_farm_assignments_role_check CHECK (role IN ('primary', 'secondary', 'specialist', 'coordinator')),
    CONSTRAINT agent_farm_assignments_allocated_funds_positive CHECK (allocated_funds_usd >= 0),
    CONSTRAINT agent_farm_assignments_weight_check CHECK (assignment_weight >= 0 AND assignment_weight <= 1)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_agent_farm_assignments_agent_id ON agent_farm_assignments(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_farm_assignments_farm_id ON agent_farm_assignments(farm_id);
CREATE INDEX IF NOT EXISTS idx_agent_farm_assignments_is_active ON agent_farm_assignments(is_active);

-- Farm-Goal assignments table
CREATE TABLE IF NOT EXISTS farm_goal_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    goal_id UUID NOT NULL REFERENCES goals(goal_id) ON DELETE CASCADE,
    contribution_weight DECIMAL(3,2) DEFAULT 1.0, -- How much this farm contributes to goal
    target_metrics JSONB DEFAULT '{}',
    current_metrics JSONB DEFAULT '{}',
    progress_percentage DECIMAL(5,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT farm_goal_assignments_unique UNIQUE(farm_id, goal_id),
    CONSTRAINT farm_goal_assignments_contribution_weight_check CHECK (contribution_weight >= 0 AND contribution_weight <= 1),
    CONSTRAINT farm_goal_assignments_progress_check CHECK (progress_percentage >= 0 AND progress_percentage <= 100)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_farm_goal_assignments_farm_id ON farm_goal_assignments(farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_goal_assignments_goal_id ON farm_goal_assignments(goal_id);
CREATE INDEX IF NOT EXISTS idx_farm_goal_assignments_is_active ON farm_goal_assignments(is_active);

-- =====================================================
-- AGENT TABLE UPDATES
-- =====================================================

-- Check if agent_configs table exists (it should from previous schema)
-- Add new columns for wallet integration
DO $$
BEGIN
    -- Add wallet integration columns to existing agent_configs table
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agent_configs' AND column_name='wallet_address') THEN
        ALTER TABLE agent_configs ADD COLUMN wallet_address VARCHAR(255);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agent_configs' AND column_name='allocated_funds_usd') THEN
        ALTER TABLE agent_configs ADD COLUMN allocated_funds_usd DECIMAL(20,8) DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agent_configs' AND column_name='farm_id') THEN
        ALTER TABLE agent_configs ADD COLUMN farm_id UUID REFERENCES farms(farm_id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agent_configs' AND column_name='assigned_goals') THEN
        ALTER TABLE agent_configs ADD COLUMN assigned_goals JSONB DEFAULT '[]';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agent_configs' AND column_name='wallet_performance') THEN
        ALTER TABLE agent_configs ADD COLUMN wallet_performance JSONB DEFAULT '{}';
    END IF;
END
$$;

-- Create index on farm_id for agents
CREATE INDEX IF NOT EXISTS idx_agent_configs_farm_id ON agent_configs(farm_id);

-- =====================================================
-- ADD FOREIGN KEY CONSTRAINTS (After all tables created)
-- =====================================================

-- Add foreign key constraints now that all tables exist
ALTER TABLE fund_allocations 
    ADD CONSTRAINT fk_fund_allocations_wallet_id 
    FOREIGN KEY (wallet_id) REFERENCES master_wallets(wallet_id) ON DELETE CASCADE;

ALTER TABLE wallet_transactions 
    ADD CONSTRAINT fk_wallet_transactions_wallet_id 
    FOREIGN KEY (wallet_id) REFERENCES master_wallets(wallet_id) ON DELETE CASCADE;

-- =====================================================
-- AUTOMATIC TIMESTAMP UPDATES
-- =====================================================

-- Function to update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_farms_updated_at BEFORE UPDATE ON farms FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_goals_updated_at BEFORE UPDATE ON goals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_master_wallets_updated_at BEFORE UPDATE ON master_wallets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_fund_allocations_updated_at BEFORE UPDATE ON fund_allocations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_agent_farm_assignments_updated_at BEFORE UPDATE ON agent_farm_assignments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_farm_goal_assignments_updated_at BEFORE UPDATE ON farm_goal_assignments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE farms ENABLE ROW LEVEL SECURITY;
ALTER TABLE goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE master_wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE fund_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallet_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_farm_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_goal_assignments ENABLE ROW LEVEL SECURITY;

-- Create policies for authenticated users (adjust based on your auth requirements)
-- Farm policies
CREATE POLICY "Authenticated users can view farms" ON farms FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can insert farms" ON farms FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can update farms" ON farms FOR UPDATE USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can delete farms" ON farms FOR DELETE USING (auth.role() = 'authenticated');

-- Goal policies
CREATE POLICY "Authenticated users can view goals" ON goals FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can insert goals" ON goals FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can update goals" ON goals FOR UPDATE USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can delete goals" ON goals FOR DELETE USING (auth.role() = 'authenticated');

-- Master wallet policies
CREATE POLICY "Authenticated users can view master_wallets" ON master_wallets FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can insert master_wallets" ON master_wallets FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can update master_wallets" ON master_wallets FOR UPDATE USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can delete master_wallets" ON master_wallets FOR DELETE USING (auth.role() = 'authenticated');

-- Fund allocation policies
CREATE POLICY "Authenticated users can view fund_allocations" ON fund_allocations FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can insert fund_allocations" ON fund_allocations FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can update fund_allocations" ON fund_allocations FOR UPDATE USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can delete fund_allocations" ON fund_allocations FOR DELETE USING (auth.role() = 'authenticated');

-- Wallet transaction policies
CREATE POLICY "Authenticated users can view wallet_transactions" ON wallet_transactions FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can insert wallet_transactions" ON wallet_transactions FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can update wallet_transactions" ON wallet_transactions FOR UPDATE USING (auth.role() = 'authenticated');

-- Assignment policies
CREATE POLICY "Authenticated users can view agent_farm_assignments" ON agent_farm_assignments FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can insert agent_farm_assignments" ON agent_farm_assignments FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can update agent_farm_assignments" ON agent_farm_assignments FOR UPDATE USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can delete agent_farm_assignments" ON agent_farm_assignments FOR DELETE USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can view farm_goal_assignments" ON farm_goal_assignments FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can insert farm_goal_assignments" ON farm_goal_assignments FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can update farm_goal_assignments" ON farm_goal_assignments FOR UPDATE USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can delete farm_goal_assignments" ON farm_goal_assignments FOR DELETE USING (auth.role() = 'authenticated');

-- =====================================================
-- SAMPLE DATA INSERT (Optional - for testing)
-- =====================================================

-- Insert sample farm types
INSERT INTO farms (name, description, farm_type, configuration) VALUES
    ('Trend Following Farm', 'Agents specializing in trend-following strategies', 'trend_following', '{"strategies": ["williams_alligator", "elliott_wave"], "risk_profile": "moderate"}'),
    ('Breakout Farm', 'Agents specializing in breakout and momentum strategies', 'breakout', '{"strategies": ["darvas_box", "renko"], "risk_profile": "aggressive"}'),
    ('Price Action Farm', 'Agents specializing in pure price action trading', 'price_action', '{"strategies": ["heikin_ashi", "candlestick_patterns"], "risk_profile": "conservative"}')
ON CONFLICT (name) DO NOTHING;

-- Insert sample goals
INSERT INTO goals (name, description, goal_type, target_criteria) VALUES
    ('200 Trades Target', 'Complete 200 profitable trades within 30 days', 'trade_volume', '{"total_trades": 200, "timeframe_days": 30, "min_profit_per_trade": 5}'),
    ('$5 Average Profit', 'Maintain $5 average profit per trade over 100 trades', 'profit_target', '{"avg_profit_per_trade": 5, "min_trades": 100, "timeframe_days": 30}'),
    ('Sharpe Ratio Excellence', 'Achieve Sharpe ratio above 2.0 with max 5% drawdown', 'strategy_performance', '{"min_sharpe_ratio": 2.0, "max_drawdown": 0.05, "timeframe_days": 30}')
ON CONFLICT (name) DO NOTHING;

-- Insert sample master wallet
INSERT INTO master_wallets (name, description, configuration) VALUES
    ('Main Trading Wallet', 'Primary wallet for autonomous trading operations', '{"auto_distribution": true, "risk_limits": {"max_allocation_per_agent": 0.1, "daily_loss_limit": 0.05}, "supported_chains": ["ethereum", "polygon", "bsc"]}')
ON CONFLICT (name) DO NOTHING;

-- =====================================================
-- END OF MIGRATION
-- =====================================================

COMMENT ON TABLE farms IS 'Farm management system for organizing trading agents into strategy-based groups';
COMMENT ON TABLE goals IS 'Goal tracking system for autonomous trading objectives';
COMMENT ON TABLE master_wallets IS 'Master wallet management for autonomous fund distribution';
COMMENT ON TABLE fund_allocations IS 'Fund allocation tracking between wallets and entities';
COMMENT ON TABLE wallet_transactions IS 'Complete transaction history for all wallet operations';
COMMENT ON TABLE agent_farm_assignments IS 'Many-to-many relationship between agents and farms';
COMMENT ON TABLE farm_goal_assignments IS 'Many-to-many relationship between farms and goals';