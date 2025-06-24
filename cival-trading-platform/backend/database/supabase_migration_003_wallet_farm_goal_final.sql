-- =====================================================
-- Supabase Migration: Wallet-Farm-Goal Integration (FINAL)
-- Version: 003-final
-- Description: Works with existing database structure - no assumptions about missing tables
-- Compatible with: wallets, wallet_transactions, trading_agents, and all existing tables
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
    wallet_id UUID, -- Reference to existing wallets table
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

-- =====================================================
-- MASTER WALLET MANAGEMENT (Works with existing wallets)
-- =====================================================

-- Master wallet configurations (extends existing wallets table)
CREATE TABLE IF NOT EXISTS master_wallet_configs (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID NOT NULL, -- References existing wallets table
    name VARCHAR(255) NOT NULL,
    description TEXT,
    configuration JSONB NOT NULL DEFAULT '{}',
    auto_distribution_enabled BOOLEAN DEFAULT true,
    emergency_stop_enabled BOOLEAN DEFAULT false,
    risk_settings JSONB DEFAULT '{}',
    performance_metrics JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT master_wallet_configs_name_unique UNIQUE(name),
    CONSTRAINT master_wallet_configs_wallet_unique UNIQUE(wallet_id)
);

-- =====================================================
-- FUND ALLOCATION TABLES (Compatible with existing wallets)
-- =====================================================

-- Fund allocations table (uses existing wallet structure)
CREATE TABLE IF NOT EXISTS fund_allocations (
    allocation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_wallet_id UUID NOT NULL, -- References existing wallets table
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

-- =====================================================
-- RELATIONSHIP TABLES
-- =====================================================

-- Agent-Farm assignments table
CREATE TABLE IF NOT EXISTS agent_farm_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    farm_id UUID NOT NULL,
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

-- Farm-Goal assignments table
CREATE TABLE IF NOT EXISTS farm_goal_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL,
    goal_id UUID NOT NULL,
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

-- =====================================================
-- EXTEND EXISTING TABLES (ONLY IF THEY EXIST)
-- =====================================================

-- Add farm and goal integration to existing trading_agents table (if it exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'trading_agents') THEN
        -- Add farm_id column
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trading_agents' AND column_name='farm_id') THEN
            ALTER TABLE trading_agents ADD COLUMN farm_id UUID;
        END IF;
        
        -- Add assigned_goals column
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trading_agents' AND column_name='assigned_goals') THEN
            ALTER TABLE trading_agents ADD COLUMN assigned_goals JSONB DEFAULT '[]';
        END IF;
        
        -- Add wallet_performance column
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trading_agents' AND column_name='wallet_performance') THEN
            ALTER TABLE trading_agents ADD COLUMN wallet_performance JSONB DEFAULT '{}';
        END IF;
        
        RAISE NOTICE 'Extended trading_agents table with farm/goal integration';
    ELSE
        RAISE NOTICE 'trading_agents table does not exist - skipping extension';
    END IF;
END
$$;

-- =====================================================
-- CREATE INDEXES
-- =====================================================

-- Farm indexes
CREATE INDEX IF NOT EXISTS idx_farms_farm_type ON farms(farm_type);
CREATE INDEX IF NOT EXISTS idx_farms_is_active ON farms(is_active);
CREATE INDEX IF NOT EXISTS idx_farms_wallet_id ON farms(wallet_id);
CREATE INDEX IF NOT EXISTS idx_farms_created_at ON farms(created_at);

-- Goal indexes
CREATE INDEX IF NOT EXISTS idx_goals_goal_type ON goals(goal_type);
CREATE INDEX IF NOT EXISTS idx_goals_completion_status ON goals(completion_status);
CREATE INDEX IF NOT EXISTS idx_goals_priority ON goals(priority);
CREATE INDEX IF NOT EXISTS idx_goals_deadline ON goals(deadline);

-- Master wallet config indexes
CREATE INDEX IF NOT EXISTS idx_master_wallet_configs_wallet_id ON master_wallet_configs(wallet_id);
CREATE INDEX IF NOT EXISTS idx_master_wallet_configs_is_active ON master_wallet_configs(is_active);

-- Fund allocation indexes
CREATE INDEX IF NOT EXISTS idx_fund_allocations_source_wallet_id ON fund_allocations(source_wallet_id);
CREATE INDEX IF NOT EXISTS idx_fund_allocations_target_type ON fund_allocations(target_type);
CREATE INDEX IF NOT EXISTS idx_fund_allocations_target_id ON fund_allocations(target_id);
CREATE INDEX IF NOT EXISTS idx_fund_allocations_is_active ON fund_allocations(is_active);

-- Assignment indexes
CREATE INDEX IF NOT EXISTS idx_agent_farm_assignments_agent_id ON agent_farm_assignments(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_farm_assignments_farm_id ON agent_farm_assignments(farm_id);
CREATE INDEX IF NOT EXISTS idx_agent_farm_assignments_is_active ON agent_farm_assignments(is_active);

CREATE INDEX IF NOT EXISTS idx_farm_goal_assignments_farm_id ON farm_goal_assignments(farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_goal_assignments_goal_id ON farm_goal_assignments(goal_id);
CREATE INDEX IF NOT EXISTS idx_farm_goal_assignments_is_active ON farm_goal_assignments(is_active);

-- Indexes for trading_agents extensions (only if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'trading_agents') THEN
        CREATE INDEX IF NOT EXISTS idx_trading_agents_farm_id ON trading_agents(farm_id) WHERE farm_id IS NOT NULL;
        RAISE NOTICE 'Created indexes for trading_agents farm integration';
    END IF;
END
$$;

-- =====================================================
-- ADD FOREIGN KEY CONSTRAINTS (ONLY TO EXISTING TABLES)
-- =====================================================

DO $$
BEGIN
    -- Farm to wallet foreign key (only if wallets table exists)
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'wallets') THEN
        -- Check if wallets table has 'id' column (common pattern)
        IF EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'wallets' AND column_name = 'id') THEN
            IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                          WHERE constraint_name = 'fk_farms_wallet_id' 
                          AND table_name = 'farms') THEN
                ALTER TABLE farms 
                    ADD CONSTRAINT fk_farms_wallet_id 
                    FOREIGN KEY (wallet_id) REFERENCES wallets(id) ON DELETE SET NULL;
                RAISE NOTICE 'Added farms -> wallets foreign key';
            END IF;
            
            -- Master wallet configs to wallets foreign key
            IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                          WHERE constraint_name = 'fk_master_wallet_configs_wallet_id' 
                          AND table_name = 'master_wallet_configs') THEN
                ALTER TABLE master_wallet_configs 
                    ADD CONSTRAINT fk_master_wallet_configs_wallet_id 
                    FOREIGN KEY (wallet_id) REFERENCES wallets(id) ON DELETE CASCADE;
                RAISE NOTICE 'Added master_wallet_configs -> wallets foreign key';
            END IF;
            
            -- Fund allocations to wallets foreign key
            IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                          WHERE constraint_name = 'fk_fund_allocations_source_wallet_id' 
                          AND table_name = 'fund_allocations') THEN
                ALTER TABLE fund_allocations 
                    ADD CONSTRAINT fk_fund_allocations_source_wallet_id 
                    FOREIGN KEY (source_wallet_id) REFERENCES wallets(id) ON DELETE CASCADE;
                RAISE NOTICE 'Added fund_allocations -> wallets foreign key';
            END IF;
        ELSE
            RAISE NOTICE 'wallets table exists but id column not found - skipping wallet foreign keys';
        END IF;
    ELSE
        RAISE NOTICE 'wallets table does not exist - skipping wallet foreign keys';
    END IF;
    
    -- Agent farm assignments to farms foreign key
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                  WHERE constraint_name = 'fk_agent_farm_assignments_farm_id' 
                  AND table_name = 'agent_farm_assignments') THEN
        ALTER TABLE agent_farm_assignments 
            ADD CONSTRAINT fk_agent_farm_assignments_farm_id 
            FOREIGN KEY (farm_id) REFERENCES farms(farm_id) ON DELETE CASCADE;
        RAISE NOTICE 'Added agent_farm_assignments -> farms foreign key';
    END IF;
    
    -- Farm goal assignments foreign keys
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                  WHERE constraint_name = 'fk_farm_goal_assignments_farm_id' 
                  AND table_name = 'farm_goal_assignments') THEN
        ALTER TABLE farm_goal_assignments 
            ADD CONSTRAINT fk_farm_goal_assignments_farm_id 
            FOREIGN KEY (farm_id) REFERENCES farms(farm_id) ON DELETE CASCADE;
        RAISE NOTICE 'Added farm_goal_assignments -> farms foreign key';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                  WHERE constraint_name = 'fk_farm_goal_assignments_goal_id' 
                  AND table_name = 'farm_goal_assignments') THEN
        ALTER TABLE farm_goal_assignments 
            ADD CONSTRAINT fk_farm_goal_assignments_goal_id 
            FOREIGN KEY (goal_id) REFERENCES goals(goal_id) ON DELETE CASCADE;
        RAISE NOTICE 'Added farm_goal_assignments -> goals foreign key';
    END IF;
    
    -- Trading agents to farms foreign key (only if trading_agents exists)
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'trading_agents') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                      WHERE constraint_name = 'fk_trading_agents_farm_id' 
                      AND table_name = 'trading_agents') THEN
            ALTER TABLE trading_agents 
                ADD CONSTRAINT fk_trading_agents_farm_id 
                FOREIGN KEY (farm_id) REFERENCES farms(farm_id) ON DELETE SET NULL;
            RAISE NOTICE 'Added trading_agents -> farms foreign key';
        END IF;
    END IF;
END
$$;

-- =====================================================
-- AUTOMATIC TIMESTAMP UPDATES
-- =====================================================

-- Function to update timestamp (create if not exists)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
DROP TRIGGER IF EXISTS update_farms_updated_at ON farms;
CREATE TRIGGER update_farms_updated_at BEFORE UPDATE ON farms FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_goals_updated_at ON goals;
CREATE TRIGGER update_goals_updated_at BEFORE UPDATE ON goals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_master_wallet_configs_updated_at ON master_wallet_configs;
CREATE TRIGGER update_master_wallet_configs_updated_at BEFORE UPDATE ON master_wallet_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_fund_allocations_updated_at ON fund_allocations;
CREATE TRIGGER update_fund_allocations_updated_at BEFORE UPDATE ON fund_allocations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_agent_farm_assignments_updated_at ON agent_farm_assignments;
CREATE TRIGGER update_agent_farm_assignments_updated_at BEFORE UPDATE ON agent_farm_assignments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_farm_goal_assignments_updated_at ON farm_goal_assignments;
CREATE TRIGGER update_farm_goal_assignments_updated_at BEFORE UPDATE ON farm_goal_assignments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on new tables
ALTER TABLE farms ENABLE ROW LEVEL SECURITY;
ALTER TABLE goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE master_wallet_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE fund_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_farm_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_goal_assignments ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (to avoid conflicts)
DROP POLICY IF EXISTS "Authenticated users can view farms" ON farms;
DROP POLICY IF EXISTS "Authenticated users can insert farms" ON farms;
DROP POLICY IF EXISTS "Authenticated users can update farms" ON farms;
DROP POLICY IF EXISTS "Authenticated users can delete farms" ON farms;

-- Create policies for authenticated users
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

-- Master wallet config policies
CREATE POLICY "Authenticated users can view master_wallet_configs" ON master_wallet_configs FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can insert master_wallet_configs" ON master_wallet_configs FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can update master_wallet_configs" ON master_wallet_configs FOR UPDATE USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can delete master_wallet_configs" ON master_wallet_configs FOR DELETE USING (auth.role() = 'authenticated');

-- Fund allocation policies
CREATE POLICY "Authenticated users can view fund_allocations" ON fund_allocations FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can insert fund_allocations" ON fund_allocations FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can update fund_allocations" ON fund_allocations FOR UPDATE USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can delete fund_allocations" ON fund_allocations FOR DELETE USING (auth.role() = 'authenticated');

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

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Show what was created
SELECT 'SUCCESS: Created ' || COUNT(*) || ' new tables for wallet-farm-goal integration' as result
FROM information_schema.tables 
WHERE table_name IN ('farms', 'goals', 'master_wallet_configs', 'fund_allocations', 'agent_farm_assignments', 'farm_goal_assignments');

-- Show existing wallets integration
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'wallets') THEN
        RAISE NOTICE 'SUCCESS: Integrated with existing wallets table containing % wallets', (SELECT COUNT(*) FROM wallets);
    ELSE
        RAISE NOTICE 'INFO: No existing wallets table found - farm/goal system ready for future wallet integration';
    END IF;
END
$$;

-- Show existing trading_agents integration
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'trading_agents') THEN
        RAISE NOTICE 'SUCCESS: Extended existing trading_agents table with farm/goal integration';
    ELSE
        RAISE NOTICE 'INFO: No existing trading_agents table found - ready for future agent integration';
    END IF;
END
$$;

-- =====================================================
-- END OF MIGRATION
-- =====================================================

COMMENT ON TABLE farms IS 'Farm management system for organizing trading agents into strategy-based groups - works with existing database';
COMMENT ON TABLE goals IS 'Goal tracking system for autonomous trading objectives';
COMMENT ON TABLE master_wallet_configs IS 'Master wallet configurations extending existing wallets functionality';
COMMENT ON TABLE fund_allocations IS 'Fund allocation tracking between existing wallets and trading entities';
COMMENT ON TABLE agent_farm_assignments IS 'Many-to-many relationship between agents and farms';
COMMENT ON TABLE farm_goal_assignments IS 'Many-to-many relationship between farms and goals';