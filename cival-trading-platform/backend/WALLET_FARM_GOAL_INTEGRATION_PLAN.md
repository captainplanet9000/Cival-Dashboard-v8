# COMPREHENSIVE WALLET-FARM-GOAL INTEGRATION PLAN
## Complete System with Supabase/Redis Integration and Full AG-UI

## OVERVIEW
Complete integration plan for wallet hierarchy, farm management, goal system with full AG-UI interface integration using existing Supabase and Redis infrastructure.

## CURRENT INFRASTRUCTURE STATUS
✅ Supabase: Connected with SUPABASE_URL and SUPABASE_ANON_KEY
✅ Redis: Connected with REDIS_URL (async and sync clients)  
✅ AG-UI Service: 12 event types, real-time streaming, session management
✅ Master Wallet Models: Complete wallet system ready for integration
✅ Service Registry: Centralized service management with dependency injection
✅ Dashboard: 6-section comprehensive dashboard with real-time data

## WALLET HIERARCHY ARCHITECTURE
```
Master Wallet (Your Main Funding)
    ↓
Farm Wallets (Strategy-Based Groups)
    ├── Trend Following Farm
    ├── Breakout Farm  
    └── Price Action Farm
        ↓
Agent Wallets (Individual Agents)
            ├── Darvas Box Agent
            ├── Williams Alligator Agent
            └── Elliott Wave Agent
```

## FUND FLOW ARCHITECTURE
```
1. Master Wallet receives your deposits
2. Auto-distribution to Farm Wallets based on performance
3. Farm Wallets allocate to Agent Wallets based on agent performance
4. Goal completion triggers fund collection back to Master Wallet
5. Performance-based reallocation occurs automatically
```

## PHASE 1: DATABASE SCHEMA INTEGRATION
*Duration: 1 week*

### 1.1 Supabase Table Creation
```sql
-- Farm Management Tables
CREATE TABLE farms (
    farm_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    farm_type VARCHAR(100), -- 'trend_following', 'breakout', 'price_action'
    configuration JSONB NOT NULL DEFAULT '{}',
    wallet_address VARCHAR(255),
    total_allocated_usd DECIMAL(20,8) DEFAULT 0,
    performance_metrics JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Goal Management Tables
CREATE TABLE goals (
    goal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    goal_type VARCHAR(100), -- 'trade_volume', 'profit_target', 'strategy_performance'
    target_criteria JSONB NOT NULL, -- {"trades": 200, "profit_per_trade": 5}
    current_progress JSONB DEFAULT '{}',
    assigned_entities JSONB DEFAULT '[]', -- [{"type": "farm", "id": "..."}, {"type": "agent", "id": "..."}]
    completion_status VARCHAR(50) DEFAULT 'active', -- 'active', 'completed', 'failed'
    completion_percentage DECIMAL(5,2) DEFAULT 0,
    wallet_allocation_usd DECIMAL(20,8) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Master Wallet Tables
CREATE TABLE master_wallets (
    wallet_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    configuration JSONB NOT NULL DEFAULT '{}',
    addresses JSONB DEFAULT '[]', -- Multi-chain addresses
    balances JSONB DEFAULT '{}', -- Current balances
    total_value_usd DECIMAL(20,8) DEFAULT 0,
    performance_metrics JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Fund Allocation Tables
CREATE TABLE fund_allocations (
    allocation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID REFERENCES master_wallets(wallet_id),
    target_type VARCHAR(50) NOT NULL, -- 'agent', 'farm', 'goal'
    target_id UUID NOT NULL,
    target_name VARCHAR(255),
    allocated_amount_usd DECIMAL(20,8) NOT NULL,
    allocated_percentage DECIMAL(5,2),
    current_value_usd DECIMAL(20,8),
    performance_metrics JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Wallet Transactions
CREATE TABLE wallet_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID REFERENCES master_wallets(wallet_id),
    transaction_type VARCHAR(100) NOT NULL,
    amount DECIMAL(20,8) NOT NULL,
    asset_symbol VARCHAR(20),
    amount_usd DECIMAL(20,8),
    from_entity VARCHAR(255),
    to_entity VARCHAR(255),
    blockchain_data JSONB DEFAULT '{}', -- tx_hash, block_number, etc.
    status VARCHAR(50) DEFAULT 'pending',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confirmed_at TIMESTAMP WITH TIME ZONE
);

-- Agent-Farm Relationships
CREATE TABLE agent_farm_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    farm_id UUID REFERENCES farms(farm_id),
    role VARCHAR(100), -- 'primary', 'secondary', 'specialist'
    allocated_funds_usd DECIMAL(20,8) DEFAULT 0,
    performance_contribution JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Farm-Goal Relationships
CREATE TABLE farm_goal_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID REFERENCES farms(farm_id),
    goal_id UUID REFERENCES goals(goal_id),
    contribution_weight DECIMAL(3,2) DEFAULT 1.0, -- How much this farm contributes to goal
    target_metrics JSONB DEFAULT '{}',
    current_metrics JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 1.2 Update Existing Agent Tables
```sql
-- Add wallet integration to existing agent configurations
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS wallet_address VARCHAR(255);
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS allocated_funds_usd DECIMAL(20,8) DEFAULT 0;
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS farm_id UUID;
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS assigned_goals JSONB DEFAULT '[]';
```

## PHASE 2: WALLET HIERARCHY ARCHITECTURE
*Duration: 1 week*

### New Services to Create:
- FarmWalletService: Manages farm-level wallets and allocations
- GoalWalletService: Links goals to wallet allocations
- AgentWalletService: Individual agent wallet management
- WalletHierarchyService: Manages the entire wallet tree
- AutoCollectionService: Handles goal completion fund collection

## PHASE 3: FARM MANAGEMENT SYSTEM
*Duration: 1 week*

### Farm Service Integration
```python
class FarmManagementService:
    # Farm CRUD operations
    - create_farm(farm_config, initial_agents)
    - assign_agents_to_farm(farm_id, agent_ids)
    - allocate_funds_to_farm(farm_id, amount)
    - get_farm_performance(farm_id)
    - rebalance_farm_resources()
    
    # Integration with existing services
    - Uses current Supabase connection
    - Integrates with AgentManagementService
    - Links to MasterWalletService
    - Publishes AG-UI events
```

## PHASE 4: GOAL MANAGEMENT SYSTEM
*Duration: 1 week*

### Goal Service Integration
```python
class GoalManagementService:
    # Goal CRUD operations
    - create_goal(goal_config, target_criteria)
    - assign_goal_to_entities(goal_id, entity_ids)
    - track_goal_progress(goal_id)
    - evaluate_goal_completion(goal_id)
    - trigger_goal_completion_collection(goal_id)
    
    # Integration with wallet system
    - Links to fund allocations
    - Triggers automatic collection on completion
    - Updates AG-UI with progress events
```

## PHASE 5: COMPLETE AG-UI INTEGRATION
*Duration: 2 weeks*

### New AG-UI Event Types:
```python
ag_ui_events = {
    # Wallet Events
    "wallet_balance_update": "Real-time balance changes",
    "fund_allocation": "New fund allocations",
    "fund_collection": "Goal completion collections",
    "wallet_transaction": "All wallet transactions",
    
    # Farm Events  
    "farm_created": "New farm creation",
    "farm_performance_update": "Farm performance metrics",
    "agent_farm_assignment": "Agent assigned to farm",
    "farm_rebalance": "Farm resource rebalancing",
    
    # Goal Events
    "goal_created": "New goal creation", 
    "goal_progress_update": "Goal progress changes",
    "goal_completed": "Goal completion achieved",
    "goal_assignment": "Goal assigned to entity"
}
```

### React Dashboard Components:
- WalletManagementPanel: Master wallet control
- FarmManagementPanel: Farm oversight and control
- GoalManagementPanel: Goal creation and tracking
- Interactive data tables with real-time updates
- Drag-and-drop agent assignment
- Real-time fund allocation controls

## PHASE 6: FUNCTIONAL UI COMPONENTS
*Duration: 1 week*

### Interactive Features:
- Real-time data tables with inline editing
- Drag-and-drop for assignments
- Interactive fund allocation sliders
- Real-time performance charts
- Functional configuration panels
- Complete transaction history

## PHASE 7: INTEGRATION & TESTING
*Duration: 1 week*

### Complete MCP Integration:
- All new services registered in service registry
- Database integration testing
- AG-UI real-time update verification
- End-to-end wallet hierarchy testing
- Goal completion and collection testing

## FINAL SYSTEM ARCHITECTURE

### AG-UI Dashboard Structure:
```
📊 Unified Trading Dashboard
├── 💰 Master Wallet Control - Balance, allocations, performance
├── 🏭 Farm Management - Farm status, agent assignments, performance  
├── 🎯 Goal Dashboard - Goal progress, completion, rewards
├── 🤖 Agent Fleet - Individual agent status and performance
├── 📈 Real-time Trading - Live trades, signals, execution
├── ⚡ Performance Analytics - Complete system performance
└── ⚙️ System Configuration - All settings and controls
```

### Key Features:
- Complete Database Integration: All tables created in Supabase
- Full Wallet Hierarchy: Master → Farm → Agent wallet structure
- Real-time AG-UI: Interactive controls with live updates
- Automatic Fund Management: Performance-based allocation and collection
- Goal-Oriented Trading: Agents work toward specific objectives
- Functional Interface: Every button, table, and control fully operational

## TIMELINE: 7 WEEKS TOTAL
- Phase 1: Database Schema Integration (1 week)
- Phase 2: Wallet Hierarchy Architecture (1 week)  
- Phase 3: Farm Management System (1 week)
- Phase 4: Goal Management System (1 week)
- Phase 5: Complete AG-UI Integration (2 weeks)
- Phase 6: Functional UI Components (1 week)
- Phase 7: Integration & Testing (1 week)

This plan ensures complete integration with existing Supabase and Redis infrastructure while creating a fully functional, interactive wallet-farm-goal system with real-time AG-UI controls.