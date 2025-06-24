-- Vaults/Wallet Management Database Schema
-- Comprehensive schema for hierarchical wallet system and fund management

-- Vaults table - Core vault definitions with hierarchical structure
CREATE TABLE IF NOT EXISTS vaults (
    vault_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vault_name VARCHAR(255) NOT NULL,
    vault_type VARCHAR(50) NOT NULL CHECK (vault_type IN (
        'master', 'strategy', 'agent', 'hot', 'cold', 'staking', 
        'lending', 'liquidity', 'reserve', 'operational'
    )),
    parent_vault_id UUID REFERENCES vaults(vault_id),
    
    -- Hierarchy and relationships
    hierarchy_level INTEGER DEFAULT 0,
    hierarchy_path TEXT, -- Materialized path for efficient queries
    
    -- Status and control
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN (
        'active', 'inactive', 'locked', 'frozen', 'migrating', 'archived'
    )),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Financial tracking
    total_balance DECIMAL(20,8) DEFAULT 0,
    available_balance DECIMAL(20,8) DEFAULT 0,
    reserved_balance DECIMAL(20,8) DEFAULT 0,
    pending_balance DECIMAL(20,8) DEFAULT 0,
    
    -- Performance metrics
    total_deposits DECIMAL(20,8) DEFAULT 0,
    total_withdrawals DECIMAL(20,8) DEFAULT 0,
    net_flow DECIMAL(20,8) DEFAULT 0,
    lifetime_pnl DECIMAL(20,8) DEFAULT 0,
    
    -- Configuration
    auto_rebalance_enabled BOOLEAN DEFAULT TRUE,
    auto_compound_enabled BOOLEAN DEFAULT FALSE,
    risk_limit DECIMAL(5,4) DEFAULT 0.10,
    allocation_strategy VARCHAR(50) DEFAULT 'proportional',
    
    -- Security and access
    security_level VARCHAR(20) DEFAULT 'standard' CHECK (security_level IN (
        'basic', 'standard', 'high', 'maximum'
    )),
    multi_sig_required BOOLEAN DEFAULT FALSE,
    multi_sig_threshold INTEGER DEFAULT 2,
    withdrawal_daily_limit DECIMAL(20,8),
    
    -- Metadata
    description TEXT,
    configuration JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT positive_balances CHECK (
        total_balance >= 0 AND available_balance >= 0 AND 
        reserved_balance >= 0 AND pending_balance >= 0
    ),
    CONSTRAINT balance_consistency CHECK (
        total_balance = available_balance + reserved_balance + pending_balance
    ),
    CONSTRAINT valid_hierarchy CHECK (
        (parent_vault_id IS NULL AND hierarchy_level = 0) OR 
        (parent_vault_id IS NOT NULL AND hierarchy_level > 0)
    )
);

-- Vault balances - Multi-asset balance tracking
CREATE TABLE IF NOT EXISTS vault_balances (
    balance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
    
    -- Asset details
    asset_symbol VARCHAR(20) NOT NULL,
    asset_name VARCHAR(100),
    asset_type VARCHAR(30) DEFAULT 'crypto' CHECK (asset_type IN (
        'crypto', 'fiat', 'token', 'nft', 'derivative', 'synthetic'
    )),
    chain VARCHAR(50), -- Blockchain network
    contract_address VARCHAR(255), -- For tokens
    
    -- Balance tracking
    total_balance DECIMAL(30,18) DEFAULT 0,
    available_balance DECIMAL(30,18) DEFAULT 0,
    reserved_balance DECIMAL(30,18) DEFAULT 0,
    staked_balance DECIMAL(30,18) DEFAULT 0,
    locked_balance DECIMAL(30,18) DEFAULT 0,
    
    -- Valuation
    price_usd DECIMAL(20,8) DEFAULT 0,
    value_usd DECIMAL(20,2) DEFAULT 0,
    price_source VARCHAR(50),
    price_updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Performance
    cost_basis DECIMAL(30,18) DEFAULT 0,
    unrealized_pnl DECIMAL(20,8) DEFAULT 0,
    realized_pnl DECIMAL(20,8) DEFAULT 0,
    
    -- Timestamps
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint
    UNIQUE(vault_id, asset_symbol, chain)
);

-- Vault transactions - Comprehensive transaction history
CREATE TABLE IF NOT EXISTS vault_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
    
    -- Transaction details
    transaction_type VARCHAR(30) NOT NULL CHECK (transaction_type IN (
        'deposit', 'withdrawal', 'transfer_in', 'transfer_out', 
        'allocation', 'rebalance', 'fee', 'reward', 'dividend',
        'stake', 'unstake', 'swap', 'trade_settlement'
    )),
    
    -- Asset information
    asset_symbol VARCHAR(20) NOT NULL,
    amount DECIMAL(30,18) NOT NULL,
    amount_usd DECIMAL(20,2) DEFAULT 0,
    
    -- Transaction references
    from_vault_id UUID REFERENCES vaults(vault_id),
    to_vault_id UUID REFERENCES vaults(vault_id),
    external_address VARCHAR(255),
    
    -- Status and timing
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'processing', 'completed', 'failed', 'cancelled', 'reversed'
    )),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- External references
    blockchain_tx_hash VARCHAR(255),
    exchange_reference VARCHAR(255),
    block_number BIGINT,
    gas_fee DECIMAL(20,8) DEFAULT 0,
    
    -- Context and metadata
    initiated_by VARCHAR(255),
    reason VARCHAR(100),
    notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT valid_amount CHECK (amount != 0),
    CONSTRAINT valid_transfer CHECK (
        (transaction_type IN ('transfer_in', 'transfer_out') AND 
         (from_vault_id IS NOT NULL OR to_vault_id IS NOT NULL)) OR
        transaction_type NOT IN ('transfer_in', 'transfer_out')
    )
);

-- Vault allocations - Dynamic allocation management
CREATE TABLE IF NOT EXISTS vault_allocations (
    allocation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
    
    -- Allocation target
    target_type VARCHAR(30) NOT NULL CHECK (target_type IN (
        'agent', 'farm', 'strategy', 'vault', 'external', 'reserve'
    )),
    target_id VARCHAR(255) NOT NULL,
    target_name VARCHAR(255),
    
    -- Allocation details
    asset_symbol VARCHAR(20) NOT NULL,
    allocated_amount DECIMAL(30,18) DEFAULT 0,
    allocated_percentage DECIMAL(5,4) DEFAULT 0,
    min_allocation DECIMAL(30,18) DEFAULT 0,
    max_allocation DECIMAL(30,18),
    
    -- Status and timing
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN (
        'active', 'paused', 'pending', 'expired', 'cancelled'
    )),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Performance tracking
    initial_value_usd DECIMAL(20,2) DEFAULT 0,
    current_value_usd DECIMAL(20,2) DEFAULT 0,
    pnl_usd DECIMAL(20,2) DEFAULT 0,
    return_percentage DECIMAL(8,4) DEFAULT 0,
    
    -- Configuration
    auto_rebalance BOOLEAN DEFAULT TRUE,
    rebalance_threshold DECIMAL(5,4) DEFAULT 0.05,
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    
    -- Metadata
    allocation_strategy VARCHAR(50),
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT valid_percentage CHECK (allocated_percentage >= 0 AND allocated_percentage <= 1),
    UNIQUE(vault_id, target_type, target_id, asset_symbol)
);

-- Vault performance - Historical performance tracking
CREATE TABLE IF NOT EXISTS vault_performance (
    performance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
    
    -- Time tracking
    date DATE DEFAULT CURRENT_DATE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Balance snapshots
    total_balance_usd DECIMAL(20,2) DEFAULT 0,
    available_balance_usd DECIMAL(20,2) DEFAULT 0,
    allocated_balance_usd DECIMAL(20,2) DEFAULT 0,
    
    -- Performance metrics
    daily_pnl DECIMAL(20,2) DEFAULT 0,
    cumulative_pnl DECIMAL(20,2) DEFAULT 0,
    daily_return_pct DECIMAL(8,4) DEFAULT 0,
    cumulative_return_pct DECIMAL(8,4) DEFAULT 0,
    
    -- Risk metrics
    volatility DECIMAL(6,4) DEFAULT 0,
    sharpe_ratio DECIMAL(6,4) DEFAULT 0,
    max_drawdown DECIMAL(5,4) DEFAULT 0,
    var_95 DECIMAL(20,2) DEFAULT 0,
    
    -- Activity metrics
    transaction_count INTEGER DEFAULT 0,
    allocation_count INTEGER DEFAULT 0,
    active_strategies INTEGER DEFAULT 0,
    
    -- Flow metrics
    inflow_usd DECIMAL(20,2) DEFAULT 0,
    outflow_usd DECIMAL(20,2) DEFAULT 0,
    net_flow_usd DECIMAL(20,2) DEFAULT 0,
    
    -- Efficiency metrics
    utilization_rate DECIMAL(5,4) DEFAULT 0,
    allocation_efficiency DECIMAL(3,2) DEFAULT 0,
    
    -- Unique constraint for daily snapshots
    UNIQUE(vault_id, date)
);

-- Vault rebalancing - Rebalancing operations and history
CREATE TABLE IF NOT EXISTS vault_rebalancing (
    rebalance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
    
    -- Rebalancing details
    trigger_type VARCHAR(30) NOT NULL CHECK (trigger_type IN (
        'scheduled', 'threshold', 'manual', 'emergency', 'optimization'
    )),
    trigger_reason TEXT,
    
    -- Status and timing
    status VARCHAR(20) DEFAULT 'planned' CHECK (status IN (
        'planned', 'in_progress', 'completed', 'failed', 'cancelled'
    )),
    planned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Rebalancing targets
    target_allocations JSONB NOT NULL, -- Target allocation percentages
    current_allocations JSONB, -- Current allocation percentages
    required_moves JSONB, -- Required asset movements
    
    -- Execution tracking
    executed_moves JSONB DEFAULT '{}'::jsonb,
    total_moves INTEGER DEFAULT 0,
    completed_moves INTEGER DEFAULT 0,
    failed_moves INTEGER DEFAULT 0,
    
    -- Cost tracking
    estimated_cost DECIMAL(20,8) DEFAULT 0,
    actual_cost DECIMAL(20,8) DEFAULT 0,
    gas_fees DECIMAL(20,8) DEFAULT 0,
    slippage DECIMAL(8,4) DEFAULT 0,
    
    -- Results
    efficiency_score DECIMAL(3,2) DEFAULT 0,
    variance_reduction DECIMAL(8,4) DEFAULT 0,
    
    -- Metadata
    initiated_by VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Vault access control - Security and permissions
CREATE TABLE IF NOT EXISTS vault_access_control (
    access_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
    
    -- Access subject
    subject_type VARCHAR(20) NOT NULL CHECK (subject_type IN (
        'user', 'agent', 'farm', 'service', 'api_key'
    )),
    subject_id VARCHAR(255) NOT NULL,
    subject_name VARCHAR(255),
    
    -- Permissions
    permissions TEXT[] NOT NULL, -- Array of permission strings
    permission_level VARCHAR(20) DEFAULT 'read' CHECK (permission_level IN (
        'read', 'write', 'admin', 'owner'
    )),
    
    -- Restrictions
    daily_withdrawal_limit DECIMAL(20,8),
    asset_restrictions TEXT[], -- Restricted assets
    ip_whitelist TEXT[], -- Allowed IP addresses
    time_restrictions JSONB, -- Time-based restrictions
    
    -- Status and timing
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN (
        'active', 'suspended', 'expired', 'revoked'
    )),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit
    granted_by VARCHAR(255),
    revoked_by VARCHAR(255),
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoke_reason TEXT,
    
    -- Unique constraint
    UNIQUE(vault_id, subject_type, subject_id)
);

-- Vault alerts - Risk and operational alerts
CREATE TABLE IF NOT EXISTS vault_alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vault_id UUID NOT NULL REFERENCES vaults(vault_id) ON DELETE CASCADE,
    
    -- Alert details
    alert_type VARCHAR(30) NOT NULL CHECK (alert_type IN (
        'balance_low', 'balance_high', 'large_withdrawal', 'suspicious_activity',
        'rebalance_needed', 'allocation_drift', 'security_breach', 'system_error'
    )),
    severity VARCHAR(10) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    
    -- Context
    triggered_by VARCHAR(255),
    trigger_value DECIMAL(20,8),
    threshold_value DECIMAL(20,8),
    
    -- Status and timing
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN (
        'active', 'acknowledged', 'resolved', 'dismissed'
    )),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Response tracking
    acknowledged_by VARCHAR(255),
    resolved_by VARCHAR(255),
    resolution_notes TEXT,
    
    -- Metadata
    alert_data JSONB DEFAULT '{}'::jsonb,
    escalation_level INTEGER DEFAULT 1
);

-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_vaults_parent ON vaults(parent_vault_id);
CREATE INDEX IF NOT EXISTS idx_vaults_type ON vaults(vault_type);
CREATE INDEX IF NOT EXISTS idx_vaults_status ON vaults(status);
CREATE INDEX IF NOT EXISTS idx_vaults_hierarchy_path ON vaults(hierarchy_path);

CREATE INDEX IF NOT EXISTS idx_vault_balances_vault_id ON vault_balances(vault_id);
CREATE INDEX IF NOT EXISTS idx_vault_balances_asset ON vault_balances(asset_symbol);
CREATE INDEX IF NOT EXISTS idx_vault_balances_chain ON vault_balances(chain);

CREATE INDEX IF NOT EXISTS idx_vault_transactions_vault_id ON vault_transactions(vault_id);
CREATE INDEX IF NOT EXISTS idx_vault_transactions_type ON vault_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_vault_transactions_status ON vault_transactions(status);
CREATE INDEX IF NOT EXISTS idx_vault_transactions_created_at ON vault_transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_vault_transactions_asset ON vault_transactions(asset_symbol);

CREATE INDEX IF NOT EXISTS idx_vault_allocations_vault_id ON vault_allocations(vault_id);
CREATE INDEX IF NOT EXISTS idx_vault_allocations_target ON vault_allocations(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_vault_allocations_status ON vault_allocations(status);

CREATE INDEX IF NOT EXISTS idx_vault_performance_vault_id ON vault_performance(vault_id);
CREATE INDEX IF NOT EXISTS idx_vault_performance_date ON vault_performance(date);

CREATE INDEX IF NOT EXISTS idx_vault_rebalancing_vault_id ON vault_rebalancing(vault_id);
CREATE INDEX IF NOT EXISTS idx_vault_rebalancing_status ON vault_rebalancing(status);
CREATE INDEX IF NOT EXISTS idx_vault_rebalancing_planned_at ON vault_rebalancing(planned_at);

CREATE INDEX IF NOT EXISTS idx_vault_access_vault_id ON vault_access_control(vault_id);
CREATE INDEX IF NOT EXISTS idx_vault_access_subject ON vault_access_control(subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_vault_access_status ON vault_access_control(status);

CREATE INDEX IF NOT EXISTS idx_vault_alerts_vault_id ON vault_alerts(vault_id);
CREATE INDEX IF NOT EXISTS idx_vault_alerts_type ON vault_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_vault_alerts_severity ON vault_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_vault_alerts_status ON vault_alerts(status);
CREATE INDEX IF NOT EXISTS idx_vault_alerts_created_at ON vault_alerts(created_at);

-- Triggers and functions
CREATE OR REPLACE FUNCTION update_vault_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_vaults_updated_at 
    BEFORE UPDATE ON vaults 
    FOR EACH ROW 
    EXECUTE FUNCTION update_vault_updated_at();

CREATE TRIGGER update_vault_allocations_updated_at 
    BEFORE UPDATE ON vault_allocations 
    FOR EACH ROW 
    EXECUTE FUNCTION update_vault_updated_at();

-- Function to update hierarchy path
CREATE OR REPLACE FUNCTION update_vault_hierarchy_path()
RETURNS TRIGGER AS $$
DECLARE
    parent_path TEXT;
BEGIN
    IF NEW.parent_vault_id IS NULL THEN
        NEW.hierarchy_path = NEW.vault_id::TEXT;
        NEW.hierarchy_level = 0;
    ELSE
        SELECT hierarchy_path, hierarchy_level + 1 
        INTO parent_path, NEW.hierarchy_level
        FROM vaults 
        WHERE vault_id = NEW.parent_vault_id;
        
        NEW.hierarchy_path = parent_path || '.' || NEW.vault_id::TEXT;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_hierarchy_path 
    BEFORE INSERT OR UPDATE OF parent_vault_id ON vaults 
    FOR EACH ROW 
    EXECUTE FUNCTION update_vault_hierarchy_path();

-- Function to update vault balance from vault_balances
CREATE OR REPLACE FUNCTION update_vault_total_balance()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE vaults 
    SET total_balance = (
        SELECT COALESCE(SUM(value_usd), 0)
        FROM vault_balances 
        WHERE vault_id = COALESCE(NEW.vault_id, OLD.vault_id)
    )
    WHERE vault_id = COALESCE(NEW.vault_id, OLD.vault_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_vault_balance_insert 
    AFTER INSERT ON vault_balances 
    FOR EACH ROW 
    EXECUTE FUNCTION update_vault_total_balance();

CREATE TRIGGER trigger_update_vault_balance_update 
    AFTER UPDATE ON vault_balances 
    FOR EACH ROW 
    EXECUTE FUNCTION update_vault_total_balance();

CREATE TRIGGER trigger_update_vault_balance_delete 
    AFTER DELETE ON vault_balances 
    FOR EACH ROW 
    EXECUTE FUNCTION update_vault_total_balance();

-- Function to validate allocation percentages
CREATE OR REPLACE FUNCTION validate_allocation_percentages()
RETURNS TRIGGER AS $$
DECLARE
    total_percentage DECIMAL(5,4);
BEGIN
    SELECT COALESCE(SUM(allocated_percentage), 0) 
    INTO total_percentage
    FROM vault_allocations 
    WHERE vault_id = NEW.vault_id 
    AND status = 'active'
    AND allocation_id != COALESCE(NEW.allocation_id, '00000000-0000-0000-0000-000000000000'::UUID);
    
    IF (total_percentage + NEW.allocated_percentage) > 1.0 THEN
        RAISE EXCEPTION 'Total allocation percentage cannot exceed 100%%. Current: %%, New: %%, Total would be: %%', 
            total_percentage * 100, NEW.allocated_percentage * 100, (total_percentage + NEW.allocated_percentage) * 100;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_validate_allocation_percentages 
    BEFORE INSERT OR UPDATE ON vault_allocations 
    FOR EACH ROW 
    EXECUTE FUNCTION validate_allocation_percentages();

-- Row Level Security (RLS) policies
ALTER TABLE vaults ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault_rebalancing ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault_access_control ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault_alerts ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies
CREATE POLICY "Allow all operations on vaults" ON vaults FOR ALL USING (true);
CREATE POLICY "Allow all operations on vault_balances" ON vault_balances FOR ALL USING (true);
CREATE POLICY "Allow all operations on vault_transactions" ON vault_transactions FOR ALL USING (true);
CREATE POLICY "Allow all operations on vault_allocations" ON vault_allocations FOR ALL USING (true);
CREATE POLICY "Allow all operations on vault_performance" ON vault_performance FOR ALL USING (true);
CREATE POLICY "Allow all operations on vault_rebalancing" ON vault_rebalancing FOR ALL USING (true);
CREATE POLICY "Allow all operations on vault_access_control" ON vault_access_control FOR ALL USING (true);
CREATE POLICY "Allow all operations on vault_alerts" ON vault_alerts FOR ALL USING (true);

-- Comments for documentation
COMMENT ON TABLE vaults IS 'Core vaults table with hierarchical wallet structure';
COMMENT ON TABLE vault_balances IS 'Multi-asset balance tracking for each vault';
COMMENT ON TABLE vault_transactions IS 'Comprehensive transaction history and audit trail';
COMMENT ON TABLE vault_allocations IS 'Dynamic allocation management to agents, farms, and strategies';
COMMENT ON TABLE vault_performance IS 'Historical performance metrics and analytics';
COMMENT ON TABLE vault_rebalancing IS 'Automated rebalancing operations and optimization';
COMMENT ON TABLE vault_access_control IS 'Security and permission management';
COMMENT ON TABLE vault_alerts IS 'Risk monitoring and operational alerts';