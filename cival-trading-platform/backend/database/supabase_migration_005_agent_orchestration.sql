-- Phase 9: Autonomous Agent Orchestration System
-- Multi-agent coordination, task distribution, and lifecycle management

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Autonomous Agents Table
CREATE TABLE IF NOT EXISTS autonomous_agents (
    agent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(50) NOT NULL CHECK (agent_type IN ('specialist', 'generalist', 'coordinator', 'supervisor', 'learner', 'hybrid')),
    status VARCHAR(50) NOT NULL DEFAULT 'initializing' CHECK (status IN ('initializing', 'idle', 'busy', 'executing', 'waiting', 'error', 'maintenance', 'offline', 'terminated')),
    
    -- Capabilities and Performance
    primary_capability VARCHAR(100) NOT NULL,
    capabilities JSONB DEFAULT '[]'::jsonb,
    specialization_score DECIMAL(3,2) DEFAULT 0.5 CHECK (specialization_score >= 0.0 AND specialization_score <= 1.0),
    
    -- Resource Management
    resources JSONB DEFAULT '{}'::jsonb,
    metrics JSONB DEFAULT '{}'::jsonb,
    
    -- Lifecycle Management
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active TIMESTAMPTZ DEFAULT NOW(),
    last_health_check TIMESTAMPTZ DEFAULT NOW(),
    health_score DECIMAL(3,2) DEFAULT 1.0 CHECK (health_score >= 0.0 AND health_score <= 1.0),
    
    -- Coordination and Communication
    coordination_mode VARCHAR(50) DEFAULT 'peer_to_peer' CHECK (coordination_mode IN ('hierarchical', 'peer_to_peer', 'swarm', 'pipeline', 'market')),
    communication_protocols JSONB DEFAULT '[]'::jsonb,
    current_collaborators JSONB DEFAULT '[]'::jsonb,
    supervisor_agent_id UUID REFERENCES autonomous_agents(agent_id),
    supervised_agents JSONB DEFAULT '[]'::jsonb,
    
    -- Configuration
    configuration JSONB DEFAULT '{}'::jsonb,
    environment_variables JSONB DEFAULT '{}'::jsonb,
    version VARCHAR(20) DEFAULT '1.0.0',
    
    -- Knowledge Integration (Phase 8 connection)
    knowledge_profile_id UUID,
    active_goals JSONB DEFAULT '[]'::jsonb,
    learned_patterns JSONB DEFAULT '{}'::jsonb,
    
    -- Indexing
    created_by UUID,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent Capability Profiles Table
CREATE TABLE IF NOT EXISTS agent_capability_profiles (
    profile_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES autonomous_agents(agent_id) ON DELETE CASCADE,
    capability VARCHAR(100) NOT NULL,
    proficiency_level DECIMAL(3,2) NOT NULL CHECK (proficiency_level >= 0.0 AND proficiency_level <= 1.0),
    experience_score DECIMAL(10,2) DEFAULT 0.0,
    success_rate DECIMAL(3,2) DEFAULT 0.0 CHECK (success_rate >= 0.0 AND success_rate <= 1.0),
    average_execution_time DECIMAL(10,2) DEFAULT 0.0,
    resource_requirements JSONB DEFAULT '{}'::jsonb,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(agent_id, capability)
);

-- Autonomous Tasks Table
CREATE TABLE IF NOT EXISTS autonomous_tasks (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    task_type VARCHAR(100) NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('critical', 'high', 'medium', 'low', 'background')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'assigned', 'executing', 'completed', 'failed', 'cancelled', 'paused', 'retrying')),
    
    -- Task Definition
    requirements JSONB DEFAULT '{}'::jsonb,
    payload JSONB DEFAULT '{}'::jsonb,
    expected_output JSONB DEFAULT '{}'::jsonb,
    
    -- Assignment and Execution
    assigned_agent_id UUID REFERENCES autonomous_agents(agent_id),
    assignment_timestamp TIMESTAMPTZ,
    execution_attempts INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Lifecycle
    created_at TIMESTAMPTZ DEFAULT NOW(),
    scheduled_for TIMESTAMPTZ,
    deadline TIMESTAMPTZ,
    
    -- Results and Tracking
    result JSONB DEFAULT '{}'::jsonb,
    progress_percentage DECIMAL(5,2) DEFAULT 0.0 CHECK (progress_percentage >= 0.0 AND progress_percentage <= 100.0),
    
    -- Collaboration
    parent_workflow_id UUID,
    child_tasks JSONB DEFAULT '[]'::jsonb,
    collaboration_context JSONB DEFAULT '{}'::jsonb,
    
    -- Metadata
    created_by UUID,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent Workflows Table
CREATE TABLE IF NOT EXISTS agent_workflows (
    workflow_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    workflow_type VARCHAR(20) NOT NULL CHECK (workflow_type IN ('sequential', 'parallel', 'conditional', 'hybrid')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'assigned', 'executing', 'completed', 'failed', 'cancelled', 'paused', 'retrying')),
    
    -- Workflow Structure
    tasks JSONB DEFAULT '[]'::jsonb,
    task_dependencies JSONB DEFAULT '{}'::jsonb,
    coordination_mode VARCHAR(50) DEFAULT 'hierarchical' CHECK (coordination_mode IN ('hierarchical', 'peer_to_peer', 'swarm', 'pipeline', 'market')),
    
    -- Agent Assignment
    participating_agents JSONB DEFAULT '[]'::jsonb,
    coordinator_agent_id UUID REFERENCES autonomous_agents(agent_id),
    agent_roles JSONB DEFAULT '{}'::jsonb,
    
    -- Execution Control
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    progress_percentage DECIMAL(5,2) DEFAULT 0.0 CHECK (progress_percentage >= 0.0 AND progress_percentage <= 100.0),
    
    -- Results and Metrics
    workflow_result JSONB DEFAULT '{}'::jsonb,
    performance_metrics JSONB DEFAULT '{}'::jsonb,
    collaboration_effectiveness DECIMAL(3,2) CHECK (collaboration_effectiveness >= 0.0 AND collaboration_effectiveness <= 1.0),
    
    -- Metadata
    created_by UUID,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent Messages Table (Inter-agent communication)
CREATE TABLE IF NOT EXISTS agent_messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sender_agent_id UUID NOT NULL REFERENCES autonomous_agents(agent_id),
    recipient_agent_id UUID NOT NULL REFERENCES autonomous_agents(agent_id),
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('request', 'response', 'notification', 'coordination', 'emergency')),
    content JSONB NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('critical', 'high', 'medium', 'low', 'background')),
    
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    requires_acknowledgment BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    
    -- Context
    workflow_id UUID REFERENCES agent_workflows(workflow_id),
    task_id UUID REFERENCES autonomous_tasks(task_id),
    conversation_id UUID
);

-- Coordination Protocols Table
CREATE TABLE IF NOT EXISTS coordination_protocols (
    protocol_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    protocol_type VARCHAR(50) NOT NULL CHECK (protocol_type IN ('hierarchical', 'peer_to_peer', 'swarm', 'pipeline', 'market')),
    
    -- Protocol Rules
    coordination_rules JSONB DEFAULT '{}'::jsonb,
    communication_patterns JSONB DEFAULT '[]'::jsonb,
    conflict_resolution JSONB DEFAULT '{}'::jsonb,
    
    -- Participants
    participating_agents JSONB DEFAULT '[]'::jsonb,
    leader_agent_id UUID REFERENCES autonomous_agents(agent_id),
    
    -- Lifecycle
    created_at TIMESTAMPTZ DEFAULT NOW(),
    active BOOLEAN DEFAULT TRUE,
    version VARCHAR(20) DEFAULT '1.0.0',
    
    created_by UUID,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent Collaborations Table
CREATE TABLE IF NOT EXISTS agent_collaborations (
    collaboration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    collaboration_type VARCHAR(50) NOT NULL CHECK (collaboration_type IN ('task_sharing', 'knowledge_sharing', 'resource_sharing', 'joint_execution')),
    
    -- Participants
    participating_agents JSONB DEFAULT '[]'::jsonb,
    coordinator_agent_id UUID REFERENCES autonomous_agents(agent_id),
    collaboration_protocol UUID REFERENCES coordination_protocols(protocol_id),
    
    -- Objectives
    shared_objectives JSONB DEFAULT '[]'::jsonb,
    success_criteria JSONB DEFAULT '[]'::jsonb,
    target_outcomes JSONB DEFAULT '{}'::jsonb,
    
    -- Progress and Results
    started_at TIMESTAMPTZ DEFAULT NOW(),
    estimated_completion TIMESTAMPTZ,
    actual_completion TIMESTAMPTZ,
    progress_percentage DECIMAL(5,2) DEFAULT 0.0 CHECK (progress_percentage >= 0.0 AND progress_percentage <= 100.0),
    
    -- Effectiveness Metrics
    collaboration_metrics JSONB DEFAULT '{}'::jsonb,
    individual_contributions JSONB DEFAULT '{}'::jsonb,
    synergy_score DECIMAL(3,2) CHECK (synergy_score >= 0.0 AND synergy_score <= 1.0),
    
    created_by UUID,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Resource Pools Table
CREATE TABLE IF NOT EXISTS resource_pools (
    pool_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    pool_type VARCHAR(20) NOT NULL CHECK (pool_type IN ('compute', 'memory', 'storage', 'network', 'license')),
    
    -- Capacity
    total_capacity DECIMAL(15,2) NOT NULL,
    available_capacity DECIMAL(15,2) NOT NULL,
    reserved_capacity DECIMAL(15,2) DEFAULT 0.0,
    
    -- Allocation
    current_allocations JSONB DEFAULT '{}'::jsonb,
    allocation_policy JSONB DEFAULT '{}'::jsonb,
    
    -- Cost Management
    cost_per_unit DECIMAL(10,4) DEFAULT 0.0,
    billing_interval VARCHAR(20) DEFAULT 'hourly',
    
    -- Monitoring
    utilization_history JSONB DEFAULT '[]'::jsonb,
    performance_metrics JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent Optimizations Table
CREATE TABLE IF NOT EXISTS agent_optimizations (
    optimization_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES autonomous_agents(agent_id),
    optimization_type VARCHAR(20) NOT NULL CHECK (optimization_type IN ('performance', 'resource', 'collaboration', 'learning')),
    
    -- Analysis
    current_metrics JSONB DEFAULT '{}'::jsonb,
    bottlenecks_identified JSONB DEFAULT '[]'::jsonb,
    optimization_opportunities JSONB DEFAULT '[]'::jsonb,
    
    -- Recommendations
    recommended_changes JSONB DEFAULT '{}'::jsonb,
    expected_improvements JSONB DEFAULT '{}'::jsonb,
    implementation_complexity VARCHAR(10) DEFAULT 'medium' CHECK (implementation_complexity IN ('low', 'medium', 'high')),
    
    -- Timeline
    created_at TIMESTAMPTZ DEFAULT NOW(),
    recommended_implementation_date TIMESTAMPTZ,
    estimated_implementation_time DECIMAL(8,2), -- hours
    
    -- Validation
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    risk_assessment JSONB DEFAULT '{}'::jsonb,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'implementing', 'completed', 'rejected')),
    implemented_at TIMESTAMPTZ,
    results JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for optimal performance

-- Autonomous Agents indexes
CREATE INDEX IF NOT EXISTS idx_autonomous_agents_status ON autonomous_agents(status);
CREATE INDEX IF NOT EXISTS idx_autonomous_agents_type ON autonomous_agents(agent_type);
CREATE INDEX IF NOT EXISTS idx_autonomous_agents_capability ON autonomous_agents(primary_capability);
CREATE INDEX IF NOT EXISTS idx_autonomous_agents_supervisor ON autonomous_agents(supervisor_agent_id);
CREATE INDEX IF NOT EXISTS idx_autonomous_agents_active ON autonomous_agents(last_active);
CREATE INDEX IF NOT EXISTS idx_autonomous_agents_health ON autonomous_agents(health_score);

-- Agent Capability Profiles indexes
CREATE INDEX IF NOT EXISTS idx_capability_profiles_agent ON agent_capability_profiles(agent_id);
CREATE INDEX IF NOT EXISTS idx_capability_profiles_capability ON agent_capability_profiles(capability);
CREATE INDEX IF NOT EXISTS idx_capability_profiles_proficiency ON agent_capability_profiles(proficiency_level);

-- Autonomous Tasks indexes
CREATE INDEX IF NOT EXISTS idx_autonomous_tasks_status ON autonomous_tasks(status);
CREATE INDEX IF NOT EXISTS idx_autonomous_tasks_priority ON autonomous_tasks(priority);
CREATE INDEX IF NOT EXISTS idx_autonomous_tasks_assigned_agent ON autonomous_tasks(assigned_agent_id);
CREATE INDEX IF NOT EXISTS idx_autonomous_tasks_workflow ON autonomous_tasks(parent_workflow_id);
CREATE INDEX IF NOT EXISTS idx_autonomous_tasks_created ON autonomous_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_autonomous_tasks_deadline ON autonomous_tasks(deadline);
CREATE INDEX IF NOT EXISTS idx_autonomous_tasks_type ON autonomous_tasks(task_type);

-- Agent Workflows indexes
CREATE INDEX IF NOT EXISTS idx_agent_workflows_status ON agent_workflows(status);
CREATE INDEX IF NOT EXISTS idx_agent_workflows_coordinator ON agent_workflows(coordinator_agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_workflows_created ON agent_workflows(created_at);
CREATE INDEX IF NOT EXISTS idx_agent_workflows_type ON agent_workflows(workflow_type);

-- Agent Messages indexes
CREATE INDEX IF NOT EXISTS idx_agent_messages_sender ON agent_messages(sender_agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_recipient ON agent_messages(recipient_agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_timestamp ON agent_messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_agent_messages_workflow ON agent_messages(workflow_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_task ON agent_messages(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_type ON agent_messages(message_type);

-- Coordination Protocols indexes
CREATE INDEX IF NOT EXISTS idx_coordination_protocols_type ON coordination_protocols(protocol_type);
CREATE INDEX IF NOT EXISTS idx_coordination_protocols_active ON coordination_protocols(active);
CREATE INDEX IF NOT EXISTS idx_coordination_protocols_leader ON coordination_protocols(leader_agent_id);

-- Agent Collaborations indexes
CREATE INDEX IF NOT EXISTS idx_agent_collaborations_coordinator ON agent_collaborations(coordinator_agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_collaborations_protocol ON agent_collaborations(collaboration_protocol);
CREATE INDEX IF NOT EXISTS idx_agent_collaborations_started ON agent_collaborations(started_at);
CREATE INDEX IF NOT EXISTS idx_agent_collaborations_type ON agent_collaborations(collaboration_type);

-- Resource Pools indexes
CREATE INDEX IF NOT EXISTS idx_resource_pools_type ON resource_pools(pool_type);
CREATE INDEX IF NOT EXISTS idx_resource_pools_availability ON resource_pools(available_capacity);

-- Agent Optimizations indexes
CREATE INDEX IF NOT EXISTS idx_agent_optimizations_agent ON agent_optimizations(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_optimizations_type ON agent_optimizations(optimization_type);
CREATE INDEX IF NOT EXISTS idx_agent_optimizations_status ON agent_optimizations(status);
CREATE INDEX IF NOT EXISTS idx_agent_optimizations_created ON agent_optimizations(created_at);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_autonomous_agents_name_search ON autonomous_agents USING gin(to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_autonomous_tasks_name_search ON autonomous_tasks USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));
CREATE INDEX IF NOT EXISTS idx_agent_workflows_name_search ON agent_workflows USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));

-- JSONB indexes for capability search
CREATE INDEX IF NOT EXISTS idx_autonomous_agents_capabilities_gin ON autonomous_agents USING gin(capabilities);
CREATE INDEX IF NOT EXISTS idx_autonomous_tasks_requirements_gin ON autonomous_tasks USING gin(requirements);
CREATE INDEX IF NOT EXISTS idx_agent_workflows_agents_gin ON agent_workflows USING gin(participating_agents);

-- Row Level Security (RLS) Policies

-- Enable RLS on all tables
ALTER TABLE autonomous_agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_capability_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE autonomous_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE coordination_protocols ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_collaborations ENABLE ROW LEVEL SECURITY;
ALTER TABLE resource_pools ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_optimizations ENABLE ROW LEVEL SECURITY;

-- Create policies for authenticated users
CREATE POLICY "Users can view autonomous agents" ON autonomous_agents
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Users can create autonomous agents" ON autonomous_agents
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Users can update their autonomous agents" ON autonomous_agents
    FOR UPDATE USING (auth.role() = 'authenticated');

-- Similar policies for other tables
CREATE POLICY "Users can manage capability profiles" ON agent_capability_profiles
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Users can manage autonomous tasks" ON autonomous_tasks
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Users can manage workflows" ON agent_workflows
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Users can manage messages" ON agent_messages
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Users can manage protocols" ON coordination_protocols
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Users can manage collaborations" ON agent_collaborations
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Users can view resource pools" ON resource_pools
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Users can manage optimizations" ON agent_optimizations
    FOR ALL USING (auth.role() = 'authenticated');

-- Create updated_at triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_autonomous_agents_updated_at BEFORE UPDATE ON autonomous_agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_autonomous_tasks_updated_at BEFORE UPDATE ON autonomous_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_workflows_updated_at BEFORE UPDATE ON agent_workflows
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_coordination_protocols_updated_at BEFORE UPDATE ON coordination_protocols
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_collaborations_updated_at BEFORE UPDATE ON agent_collaborations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_resource_pools_updated_at BEFORE UPDATE ON resource_pools
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create functions for common operations

-- Function to calculate agent utilization
CREATE OR REPLACE FUNCTION calculate_agent_utilization(agent_uuid UUID)
RETURNS DECIMAL AS $$
DECLARE
    total_tasks INTEGER;
    active_tasks INTEGER;
    utilization DECIMAL;
BEGIN
    SELECT COUNT(*) INTO total_tasks
    FROM autonomous_tasks
    WHERE assigned_agent_id = agent_uuid
    AND created_at >= NOW() - INTERVAL '24 hours';
    
    SELECT COUNT(*) INTO active_tasks
    FROM autonomous_tasks
    WHERE assigned_agent_id = agent_uuid
    AND status IN ('assigned', 'executing')
    AND created_at >= NOW() - INTERVAL '24 hours';
    
    IF total_tasks = 0 THEN
        RETURN 0.0;
    END IF;
    
    utilization := (active_tasks::DECIMAL / total_tasks::DECIMAL) * 100;
    RETURN ROUND(utilization, 2);
END;
$$ LANGUAGE plpgsql;

-- Function to get agent performance metrics
CREATE OR REPLACE FUNCTION get_agent_performance_metrics(agent_uuid UUID)
RETURNS JSONB AS $$
DECLARE
    metrics JSONB;
    completed_tasks INTEGER;
    failed_tasks INTEGER;
    avg_execution_time DECIMAL;
    success_rate DECIMAL;
BEGIN
    SELECT 
        COUNT(*) FILTER (WHERE status = 'completed'),
        COUNT(*) FILTER (WHERE status = 'failed'),
        AVG(EXTRACT(EPOCH FROM (completed_at - assignment_timestamp)))
    INTO completed_tasks, failed_tasks, avg_execution_time
    FROM autonomous_tasks
    WHERE assigned_agent_id = agent_uuid
    AND assignment_timestamp >= NOW() - INTERVAL '7 days';
    
    IF (completed_tasks + failed_tasks) = 0 THEN
        success_rate := 0.0;
    ELSE
        success_rate := (completed_tasks::DECIMAL / (completed_tasks + failed_tasks)::DECIMAL) * 100;
    END IF;
    
    metrics := jsonb_build_object(
        'completed_tasks', completed_tasks,
        'failed_tasks', failed_tasks,
        'success_rate', ROUND(success_rate, 2),
        'avg_execution_time', ROUND(COALESCE(avg_execution_time, 0), 2),
        'calculated_at', NOW()
    );
    
    RETURN metrics;
END;
$$ LANGUAGE plpgsql;

-- Insert some sample data for development
INSERT INTO resource_pools (name, pool_type, total_capacity, available_capacity, cost_per_unit)
VALUES 
    ('Primary Compute Pool', 'compute', 1000.0, 1000.0, 0.10),
    ('Memory Pool Alpha', 'memory', 2048.0, 2048.0, 0.05),
    ('Storage Pool Beta', 'storage', 10240.0, 10240.0, 0.02),
    ('Network Bandwidth Pool', 'network', 1000.0, 1000.0, 0.01);

INSERT INTO coordination_protocols (name, description, protocol_type, coordination_rules)
VALUES 
    ('Standard Hierarchical', 'Standard top-down coordination protocol', 'hierarchical', '{"max_depth": 3, "communication_latency": 100}'::jsonb),
    ('Peer Collaboration', 'Equal agent collaboration protocol', 'peer_to_peer', '{"consensus_threshold": 0.6, "max_participants": 10}'::jsonb),
    ('Swarm Intelligence', 'Emergent behavior coordination', 'swarm', '{"convergence_threshold": 0.8, "local_interaction_radius": 5}'::jsonb);

-- Commit the migration
COMMENT ON TABLE autonomous_agents IS 'Core autonomous agent definitions and metadata';
COMMENT ON TABLE agent_capability_profiles IS 'Detailed capability profiles for each agent';
COMMENT ON TABLE autonomous_tasks IS 'Task definitions and execution tracking';
COMMENT ON TABLE agent_workflows IS 'Multi-agent workflow orchestration';
COMMENT ON TABLE agent_messages IS 'Inter-agent communication messages';
COMMENT ON TABLE coordination_protocols IS 'Agent coordination protocol definitions';
COMMENT ON TABLE agent_collaborations IS 'Active agent collaboration sessions';
COMMENT ON TABLE resource_pools IS 'Shared resource pools for agent allocation';
COMMENT ON TABLE agent_optimizations IS 'Agent performance optimization recommendations';