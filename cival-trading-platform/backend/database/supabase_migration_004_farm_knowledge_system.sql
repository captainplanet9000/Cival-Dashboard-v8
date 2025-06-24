-- Farm Knowledge System Migration - Phase 8
-- Creates comprehensive tables for trading resources, knowledge management, and agent access

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Farm Resources Table
CREATE TABLE IF NOT EXISTS farm_resources (
    resource_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type TEXT NOT NULL CHECK (resource_type IN (
        'trading_books', 'standard_operating_procedures', 'trading_strategies',
        'market_data', 'market_research', 'agent_training', 'trading_logs',
        'alert_configurations', 'strategy_backtests', 'technical_documentation'
    )),
    content_format TEXT NOT NULL CHECK (content_format IN (
        'pdf', 'epub', 'txt', 'md', 'csv', 'json', 'xlsx', 'docx', 'image', 'video'
    )),
    title TEXT NOT NULL,
    description TEXT,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    content_type TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    
    -- Metadata (stored as JSONB for flexibility)
    metadata JSONB DEFAULT '{}' NOT NULL,
    tags TEXT[] DEFAULT '{}',
    categories TEXT[] DEFAULT '{}',
    
    -- Access control
    access_level TEXT DEFAULT 'public' CHECK (access_level IN (
        'public', 'restricted', 'agent_only', 'admin_only'
    )),
    restricted_to_agents TEXT[] DEFAULT '{}',
    restricted_to_users TEXT[] DEFAULT '{}',
    
    -- Processing and indexing
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN (
        'pending', 'processing', 'processed', 'indexed', 'error', 'failed'
    )),
    extracted_text TEXT,
    summary TEXT,
    key_concepts TEXT[] DEFAULT '{}',
    vector_embeddings JSONB,
    
    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE,
    popular_with_agents TEXT[] DEFAULT '{}',
    
    -- System fields
    created_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_modified TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    modified_by UUID REFERENCES auth.users(id),
    
    -- MCP and AI access
    mcp_accessible BOOLEAN DEFAULT true,
    ai_searchable BOOLEAN DEFAULT true,
    auto_suggest BOOLEAN DEFAULT true,
    
    -- Content analysis
    sentiment_score FLOAT,
    complexity_score FLOAT,
    relevance_scores JSONB DEFAULT '{}'
);

-- Resource Access Log Table
CREATE TABLE IF NOT EXISTS resource_access_log (
    access_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_id UUID NOT NULL REFERENCES farm_resources(resource_id) ON DELETE CASCADE,
    agent_id TEXT,
    user_id UUID REFERENCES auth.users(id),
    access_type TEXT DEFAULT 'read' CHECK (access_type IN (
        'read', 'download', 'search', 'reference', 'learn'
    )),
    access_method TEXT DEFAULT 'api' CHECK (access_method IN (
        'mcp', 'api', 'ui', 'direct'
    )),
    
    -- Context of access
    trading_context TEXT,
    goal_id UUID,
    session_id UUID,
    
    -- Access details
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    duration_seconds INTEGER,
    pages_viewed INTEGER[],
    content_extracted TEXT,
    
    -- Usage metrics
    was_helpful BOOLEAN,
    usage_rating INTEGER CHECK (usage_rating >= 1 AND usage_rating <= 5),
    notes TEXT
);

-- Resource Learning Paths Table
CREATE TABLE IF NOT EXISTS resource_learning_paths (
    path_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    path_name TEXT NOT NULL,
    description TEXT NOT NULL,
    target_skill_level TEXT CHECK (target_skill_level IN ('beginner', 'intermediate', 'advanced')),
    estimated_duration_hours INTEGER NOT NULL,
    
    -- Path structure
    resources_sequence UUID[] NOT NULL,
    prerequisites TEXT[] DEFAULT '{}',
    learning_objectives TEXT[] DEFAULT '{}',
    
    -- Agent assignment
    assigned_agents TEXT[] DEFAULT '{}',
    completion_tracking JSONB DEFAULT '{}',
    
    -- Path metadata
    created_by UUID NOT NULL REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Agent Knowledge Profiles Table
CREATE TABLE IF NOT EXISTS agent_knowledge_profiles (
    agent_id TEXT PRIMARY KEY,
    knowledge_areas JSONB DEFAULT '{}',
    completed_resources UUID[] DEFAULT '{}',
    in_progress_resources UUID[] DEFAULT '{}',
    favorite_resources UUID[] DEFAULT '{}',
    
    -- Learning metrics
    total_learning_time_hours FLOAT DEFAULT 0.0,
    resources_completed_count INTEGER DEFAULT 0,
    average_comprehension_score FLOAT DEFAULT 0.0,
    learning_velocity FLOAT DEFAULT 0.0,
    
    -- Preferences
    preferred_content_types TEXT[] DEFAULT '{}',
    preferred_difficulty_level TEXT,
    learning_schedule_preferences JSONB DEFAULT '{}',
    
    -- Performance correlation
    knowledge_to_performance_correlation JSONB DEFAULT '{}',
    last_performance_update TIMESTAMP WITH TIME ZONE,
    
    -- System fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Knowledge Recommendations Table
CREATE TABLE IF NOT EXISTS knowledge_recommendations (
    recommendation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id TEXT NOT NULL,
    resource_id UUID NOT NULL REFERENCES farm_resources(resource_id) ON DELETE CASCADE,
    recommendation_type TEXT NOT NULL CHECK (recommendation_type IN (
        'skill_gap', 'performance_improvement', 'goal_related', 'trending', 'collaborative'
    )),
    
    -- Recommendation details
    reason TEXT NOT NULL,
    confidence_score FLOAT NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    estimated_impact TEXT,
    
    -- Context
    triggered_by TEXT,
    goal_context TEXT,
    performance_context JSONB,
    
    -- Recommendation lifecycle
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending', 'viewed', 'accepted', 'rejected', 'expired'
    )),
    agent_feedback TEXT
);

-- Goal Knowledge Requirements Table (extends existing goal system)
CREATE TABLE IF NOT EXISTS goal_knowledge_requirements (
    requirement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID NOT NULL, -- References goals table
    knowledge_area TEXT NOT NULL,
    required_competency_level FLOAT NOT NULL CHECK (required_competency_level >= 0.0 AND required_competency_level <= 1.0),
    recommended_resources UUID[] DEFAULT '{}',
    is_critical BOOLEAN DEFAULT false,
    estimated_learning_time_hours FLOAT
);

-- Goal Resource Assignments Table
CREATE TABLE IF NOT EXISTS goal_resource_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID NOT NULL, -- References goals table
    resource_id UUID NOT NULL REFERENCES farm_resources(resource_id) ON DELETE CASCADE,
    assignment_type TEXT NOT NULL CHECK (assignment_type IN (
        'required', 'recommended', 'supplementary', 'reference'
    )),
    assigned_by UUID NOT NULL REFERENCES auth.users(id),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Usage tracking
    agent_completion_status JSONB DEFAULT '{}',
    effectiveness_rating FLOAT CHECK (effectiveness_rating >= 0.0 AND effectiveness_rating <= 1.0)
);

-- Enhanced Goals Table (if not exists, with knowledge integration)
CREATE TABLE IF NOT EXISTS goals (
    goal_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_name TEXT NOT NULL,
    goal_type TEXT NOT NULL,
    description TEXT,
    target_value DECIMAL(20,8) NOT NULL,
    current_value DECIMAL(20,8) DEFAULT 0,
    progress_percentage FLOAT DEFAULT 0,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 2,
    
    -- Knowledge integration
    knowledge_resources UUID[] DEFAULT '{}',
    llm_analysis JSONB DEFAULT '{}',
    auto_created BOOLEAN DEFAULT false,
    natural_language_input TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    target_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Assignments
    assigned_agents TEXT[] DEFAULT '{}',
    assigned_farms TEXT[] DEFAULT '{}',
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_by UUID NOT NULL REFERENCES auth.users(id)
);

-- Goal Progress Table (enhanced)
CREATE TABLE IF NOT EXISTS goal_progress (
    progress_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID NOT NULL REFERENCES goals(goal_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    current_value DECIMAL(20,8) NOT NULL,
    progress_percentage FLOAT NOT NULL,
    velocity FLOAT DEFAULT 0,
    estimated_completion TIMESTAMP WITH TIME ZONE,
    milestones_achieved TEXT[] DEFAULT '{}',
    blockers TEXT[] DEFAULT '{}',
    knowledge_applied TEXT[] DEFAULT '{}'
);

-- Goal Completions Table (enhanced)
CREATE TABLE IF NOT EXISTS goal_completions (
    completion_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID NOT NULL REFERENCES goals(goal_id) ON DELETE CASCADE,
    completion_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    final_value DECIMAL(20,8) NOT NULL,
    success_rate FLOAT NOT NULL,
    total_profit DECIMAL(20,8) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    completion_time_days INTEGER NOT NULL,
    contributing_agents TEXT[] DEFAULT '{}',
    contributing_farms TEXT[] DEFAULT '{}',
    performance_metrics JSONB DEFAULT '{}',
    knowledge_utilized TEXT[] DEFAULT '{}'
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_farm_resources_type ON farm_resources(resource_type);
CREATE INDEX IF NOT EXISTS idx_farm_resources_created_by ON farm_resources(created_by);
CREATE INDEX IF NOT EXISTS idx_farm_resources_tags ON farm_resources USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_farm_resources_access_level ON farm_resources(access_level);
CREATE INDEX IF NOT EXISTS idx_farm_resources_processing_status ON farm_resources(processing_status);

CREATE INDEX IF NOT EXISTS idx_resource_access_log_resource_id ON resource_access_log(resource_id);
CREATE INDEX IF NOT EXISTS idx_resource_access_log_agent_id ON resource_access_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_resource_access_log_accessed_at ON resource_access_log(accessed_at);

CREATE INDEX IF NOT EXISTS idx_knowledge_recommendations_agent_id ON knowledge_recommendations(agent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_recommendations_status ON knowledge_recommendations(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_recommendations_created_at ON knowledge_recommendations(created_at);

CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
CREATE INDEX IF NOT EXISTS idx_goals_created_by ON goals(created_by);
CREATE INDEX IF NOT EXISTS idx_goals_created_at ON goals(created_at);

-- Full-text search index for resources
CREATE INDEX IF NOT EXISTS idx_farm_resources_search ON farm_resources USING GIN(to_tsvector('english', title || ' ' || COALESCE(description, '') || ' ' || COALESCE(extracted_text, '')));

-- Vector similarity index (for embeddings)
-- CREATE INDEX IF NOT EXISTS idx_farm_resources_embeddings ON farm_resources USING ivfflat (vector_embeddings) WITH (lists = 100);

-- Row Level Security (RLS) Policies

-- Enable RLS on all tables
ALTER TABLE farm_resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE resource_access_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE resource_learning_paths ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_knowledge_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE goal_knowledge_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE goal_resource_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE goal_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE goal_completions ENABLE ROW LEVEL SECURITY;

-- Farm Resources Policies
CREATE POLICY "Users can view public farm resources" ON farm_resources
    FOR SELECT USING (access_level = 'public' OR created_by = auth.uid());

CREATE POLICY "Users can create farm resources" ON farm_resources
    FOR INSERT WITH CHECK (created_by = auth.uid());

CREATE POLICY "Users can update their own farm resources" ON farm_resources
    FOR UPDATE USING (created_by = auth.uid());

CREATE POLICY "Users can delete their own farm resources" ON farm_resources
    FOR DELETE USING (created_by = auth.uid());

-- Resource Access Log Policies
CREATE POLICY "Users can view their own access logs" ON resource_access_log
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can create access logs" ON resource_access_log
    FOR INSERT WITH CHECK (user_id = auth.uid());

-- Goals Policies
CREATE POLICY "Users can view their own goals" ON goals
    FOR SELECT USING (created_by = auth.uid());

CREATE POLICY "Users can create goals" ON goals
    FOR INSERT WITH CHECK (created_by = auth.uid());

CREATE POLICY "Users can update their own goals" ON goals
    FOR UPDATE USING (created_by = auth.uid());

CREATE POLICY "Users can delete their own goals" ON goals
    FOR DELETE USING (created_by = auth.uid());

-- Goal Progress Policies
CREATE POLICY "Users can view progress for their goals" ON goal_progress
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM goals 
            WHERE goals.goal_id = goal_progress.goal_id 
            AND goals.created_by = auth.uid()
        )
    );

CREATE POLICY "Users can create progress for their goals" ON goal_progress
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM goals 
            WHERE goals.goal_id = goal_progress.goal_id 
            AND goals.created_by = auth.uid()
        )
    );

-- Learning Paths Policies
CREATE POLICY "Users can view their own learning paths" ON resource_learning_paths
    FOR SELECT USING (created_by = auth.uid());

CREATE POLICY "Users can create learning paths" ON resource_learning_paths
    FOR INSERT WITH CHECK (created_by = auth.uid());

-- Functions for automated tasks

-- Function to update resource usage count
CREATE OR REPLACE FUNCTION update_resource_usage()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE farm_resources 
    SET usage_count = usage_count + 1,
        last_accessed = NEW.accessed_at
    WHERE resource_id = NEW.resource_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update usage count
CREATE TRIGGER trigger_update_resource_usage
    AFTER INSERT ON resource_access_log
    FOR EACH ROW EXECUTE FUNCTION update_resource_usage();

-- Function to update goal progress timestamp
CREATE OR REPLACE FUNCTION update_goal_modified()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE goals 
    SET last_modified = NOW()
    WHERE goal_id = NEW.goal_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update goal modification time
CREATE TRIGGER trigger_update_goal_modified
    AFTER INSERT ON goal_progress
    FOR EACH ROW EXECUTE FUNCTION update_goal_modified();

-- Function to automatically expire old recommendations
CREATE OR REPLACE FUNCTION expire_old_recommendations()
RETURNS void AS $$
BEGIN
    UPDATE knowledge_recommendations
    SET status = 'expired'
    WHERE expires_at < NOW() AND status = 'pending';
END;
$$ LANGUAGE plpgsql;

-- Grant permissions for API access
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;

-- Insert some initial resource types and categories
INSERT INTO farm_resources (
    resource_type, content_format, title, description, file_path, file_size, 
    content_type, original_filename, metadata, created_by, access_level
) VALUES 
(
    'standard_operating_procedures', 'md', 'Risk Management SOP', 
    'Standard operating procedures for risk management in algorithmic trading',
    '/system/sops/risk_management.md', 1024, 'text/markdown', 'risk_management.md',
    '{"version": "1.0", "author": "System", "difficulty_level": "intermediate"}',
    '00000000-0000-0000-0000-000000000000', 'public'
) ON CONFLICT DO NOTHING;

-- Create materialized view for resource analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS resource_usage_analytics AS
SELECT 
    fr.resource_id,
    fr.title,
    fr.resource_type,
    COUNT(ral.access_id) as total_accesses,
    COUNT(DISTINCT ral.agent_id) as unique_agents,
    AVG(ral.duration_seconds) as avg_duration,
    MAX(ral.accessed_at) as last_access,
    fr.usage_count
FROM farm_resources fr
LEFT JOIN resource_access_log ral ON fr.resource_id = ral.resource_id
GROUP BY fr.resource_id, fr.title, fr.resource_type, fr.usage_count;

-- Index for the materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_resource_usage_analytics_resource_id ON resource_usage_analytics(resource_id);

-- Refresh function for the analytics view
CREATE OR REPLACE FUNCTION refresh_resource_analytics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY resource_usage_analytics;
END;
$$ LANGUAGE plpgsql;