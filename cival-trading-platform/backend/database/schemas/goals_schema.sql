-- Goals Management Database Schema
-- Enhanced schema for comprehensive goal tracking and management

-- Goals table - Core goal definitions
CREATE TABLE IF NOT EXISTS goals (
    goal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_name VARCHAR(255) NOT NULL,
    goal_type VARCHAR(50) NOT NULL CHECK (goal_type IN (
        'profit_target', 'trade_count', 'win_rate', 'portfolio_value', 
        'risk_management', 'strategy_performance', 'time_based', 'collaborative'
    )),
    description TEXT,
    target_value DECIMAL(15,2) NOT NULL,
    current_value DECIMAL(15,2) DEFAULT 0,
    progress_percentage DECIMAL(5,2) DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'active', 'in_progress', 'completed', 'failed', 'cancelled', 'paused'
    )),
    priority INTEGER DEFAULT 2 CHECK (priority >= 1 AND priority <= 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    target_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    assigned_agents TEXT[] DEFAULT '{}',
    assigned_farms TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Indexes for performance
    CONSTRAINT valid_dates CHECK (
        target_date IS NULL OR target_date > created_at
    ),
    CONSTRAINT completed_date_check CHECK (
        (status = 'completed' AND completed_at IS NOT NULL) OR 
        (status != 'completed' AND completed_at IS NULL)
    )
);

-- Goal progress tracking - Historical progress records
CREATE TABLE IF NOT EXISTS goal_progress (
    progress_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES goals(goal_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    current_value DECIMAL(15,2) NOT NULL,
    progress_percentage DECIMAL(5,2) NOT NULL,
    velocity DECIMAL(10,4) DEFAULT 0, -- Progress per day
    estimated_completion TIMESTAMP WITH TIME ZONE,
    milestones_achieved TEXT[] DEFAULT '{}',
    blockers TEXT[] DEFAULT '{}',
    performance_data JSONB DEFAULT '{}'::jsonb,
    
    -- Indexes
    CONSTRAINT progress_percentage_check CHECK (progress_percentage >= 0 AND progress_percentage <= 100)
);

-- Goal completions - Detailed completion records
CREATE TABLE IF NOT EXISTS goal_completions (
    completion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES goals(goal_id) ON DELETE CASCADE,
    completion_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    final_value DECIMAL(15,2) NOT NULL,
    success_rate DECIMAL(5,4) DEFAULT 1.0,
    total_profit DECIMAL(15,2) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    completion_time_days INTEGER,
    contributing_agents TEXT[] DEFAULT '{}',
    contributing_farms TEXT[] DEFAULT '{}',
    performance_metrics JSONB DEFAULT '{}'::jsonb,
    collection_amount DECIMAL(15,2) DEFAULT 0,
    collection_status VARCHAR(20) DEFAULT 'pending' CHECK (collection_status IN (
        'pending', 'collecting', 'completed', 'failed'
    )),
    
    -- Auto-calculate completion time
    completion_time_days GENERATED ALWAYS AS (
        EXTRACT(DAY FROM completion_timestamp - (
            SELECT created_at FROM goals WHERE goals.goal_id = goal_completions.goal_id
        ))
    ) STORED
);

-- Goal assignments - Agent and farm assignments to goals
CREATE TABLE IF NOT EXISTS goal_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES goals(goal_id) ON DELETE CASCADE,
    assignee_type VARCHAR(10) NOT NULL CHECK (assignee_type IN ('agent', 'farm')),
    assignee_id VARCHAR(255) NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assigned_by VARCHAR(255) DEFAULT 'system',
    role VARCHAR(50) DEFAULT 'contributor',
    allocation_percentage DECIMAL(5,2) DEFAULT 0,
    performance_contribution DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'removed')),
    
    -- Unique constraint to prevent duplicate assignments
    UNIQUE(goal_id, assignee_type, assignee_id)
);

-- Goal milestones - Intermediate targets and achievements
CREATE TABLE IF NOT EXISTS goal_milestones (
    milestone_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES goals(goal_id) ON DELETE CASCADE,
    milestone_name VARCHAR(255) NOT NULL,
    milestone_description TEXT,
    target_value DECIMAL(15,2) NOT NULL,
    target_percentage DECIMAL(5,2) NOT NULL,
    achieved_at TIMESTAMP WITH TIME ZONE,
    achieved_value DECIMAL(15,2),
    is_achieved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure milestones are ordered correctly
    CONSTRAINT milestone_percentage_check CHECK (target_percentage > 0 AND target_percentage < 100)
);

-- Goal analytics - Performance analytics and insights
CREATE TABLE IF NOT EXISTS goal_analytics (
    analytics_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES goals(goal_id) ON DELETE CASCADE,
    analysis_date DATE DEFAULT CURRENT_DATE,
    metrics_snapshot JSONB NOT NULL,
    trend_analysis JSONB DEFAULT '{}'::jsonb,
    prediction_data JSONB DEFAULT '{}'::jsonb,
    recommendation TEXT,
    confidence_score DECIMAL(3,2) DEFAULT 0.5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- One analytics record per goal per day
    UNIQUE(goal_id, analysis_date)
);

-- Goal events - Audit trail and event logging
CREATE TABLE IF NOT EXISTS goal_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES goals(goal_id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}'::jsonb,
    triggered_by VARCHAR(255),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_status VARCHAR(20) DEFAULT 'pending' CHECK (processing_status IN (
        'pending', 'processing', 'completed', 'failed'
    ))
);

-- Goal templates - Reusable goal templates
CREATE TABLE IF NOT EXISTS goal_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_name VARCHAR(255) NOT NULL UNIQUE,
    template_description TEXT,
    goal_type VARCHAR(50) NOT NULL,
    default_target_value DECIMAL(15,2),
    template_config JSONB DEFAULT '{}'::jsonb,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
CREATE INDEX IF NOT EXISTS idx_goals_type ON goals(goal_type);
CREATE INDEX IF NOT EXISTS idx_goals_created_at ON goals(created_at);
CREATE INDEX IF NOT EXISTS idx_goals_target_date ON goals(target_date);
CREATE INDEX IF NOT EXISTS idx_goals_assigned_agents ON goals USING GIN(assigned_agents);
CREATE INDEX IF NOT EXISTS idx_goals_assigned_farms ON goals USING GIN(assigned_farms);

CREATE INDEX IF NOT EXISTS idx_goal_progress_goal_id ON goal_progress(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_progress_timestamp ON goal_progress(timestamp);

CREATE INDEX IF NOT EXISTS idx_goal_completions_goal_id ON goal_completions(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_completions_timestamp ON goal_completions(completion_timestamp);

CREATE INDEX IF NOT EXISTS idx_goal_assignments_goal_id ON goal_assignments(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_assignments_assignee ON goal_assignments(assignee_type, assignee_id);

CREATE INDEX IF NOT EXISTS idx_goal_milestones_goal_id ON goal_milestones(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_milestones_achieved ON goal_milestones(is_achieved);

CREATE INDEX IF NOT EXISTS idx_goal_analytics_goal_id ON goal_analytics(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_analytics_date ON goal_analytics(analysis_date);

CREATE INDEX IF NOT EXISTS idx_goal_events_goal_id ON goal_events(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_events_timestamp ON goal_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_goal_events_type ON goal_events(event_type);

-- Triggers for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_goals_updated_at 
    BEFORE UPDATE ON goals 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_goal_templates_updated_at 
    BEFORE UPDATE ON goal_templates 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically update goal progress percentage
CREATE OR REPLACE FUNCTION update_goal_progress_percentage()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the goal's current value and progress percentage
    UPDATE goals 
    SET 
        current_value = NEW.current_value,
        progress_percentage = NEW.progress_percentage,
        updated_at = NOW()
    WHERE goal_id = NEW.goal_id;
    
    -- Check if goal should be marked as completed
    IF NEW.progress_percentage >= 100 THEN
        UPDATE goals 
        SET 
            status = 'completed',
            completed_at = NOW()
        WHERE goal_id = NEW.goal_id AND status != 'completed';
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_goal_progress 
    AFTER INSERT ON goal_progress 
    FOR EACH ROW 
    EXECUTE FUNCTION update_goal_progress_percentage();

-- Function to create goal completion record when goal is completed
CREATE OR REPLACE FUNCTION create_goal_completion()
RETURNS TRIGGER AS $$
BEGIN
    -- Only create completion record when status changes to 'completed'
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        INSERT INTO goal_completions (
            goal_id,
            completion_timestamp,
            final_value,
            success_rate,
            contributing_agents,
            contributing_farms
        ) VALUES (
            NEW.goal_id,
            NEW.completed_at,
            NEW.current_value,
            CASE 
                WHEN NEW.progress_percentage >= 100 THEN 1.0
                ELSE NEW.progress_percentage / 100.0
            END,
            NEW.assigned_agents,
            NEW.assigned_farms
        );
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_create_goal_completion 
    AFTER UPDATE ON goals 
    FOR EACH ROW 
    EXECUTE FUNCTION create_goal_completion();

-- Row Level Security (RLS) policies
ALTER TABLE goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE goal_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE goal_completions ENABLE ROW LEVEL SECURITY;
ALTER TABLE goal_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE goal_milestones ENABLE ROW LEVEL SECURITY;
ALTER TABLE goal_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE goal_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE goal_templates ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies (can be customized based on authentication needs)
CREATE POLICY "Allow all operations on goals" ON goals FOR ALL USING (true);
CREATE POLICY "Allow all operations on goal_progress" ON goal_progress FOR ALL USING (true);
CREATE POLICY "Allow all operations on goal_completions" ON goal_completions FOR ALL USING (true);
CREATE POLICY "Allow all operations on goal_assignments" ON goal_assignments FOR ALL USING (true);
CREATE POLICY "Allow all operations on goal_milestones" ON goal_milestones FOR ALL USING (true);
CREATE POLICY "Allow all operations on goal_analytics" ON goal_analytics FOR ALL USING (true);
CREATE POLICY "Allow all operations on goal_events" ON goal_events FOR ALL USING (true);
CREATE POLICY "Allow all operations on goal_templates" ON goal_templates FOR ALL USING (true);

-- Insert default goal templates
INSERT INTO goal_templates (template_name, template_description, goal_type, default_target_value, template_config) VALUES
('Daily Profit Target', 'Achieve specific daily profit target', 'profit_target', 100.00, '{"timeframe": "1d", "auto_collect": true}'),
('Weekly Trade Volume', 'Execute target number of trades per week', 'trade_count', 50, '{"timeframe": "1w", "min_trade_size": 10}'),
('Monthly Win Rate', 'Maintain target win rate over a month', 'win_rate', 0.70, '{"timeframe": "1m", "min_trades": 20}'),
('Portfolio Growth', 'Achieve target portfolio value growth', 'portfolio_value', 10000.00, '{"timeframe": "3m", "compound": true}'),
('Risk Management', 'Maintain portfolio risk within limits', 'risk_management', 0.05, '{"max_drawdown": 0.05, "var_limit": 0.02}'),
('Strategy Performance', 'Achieve target strategy-specific performance', 'strategy_performance', 0.15, '{"min_sharpe": 1.5, "timeframe": "1m"}')
ON CONFLICT (template_name) DO NOTHING;

-- Comments for documentation
COMMENT ON TABLE goals IS 'Core goals table for tracking trading and portfolio objectives';
COMMENT ON TABLE goal_progress IS 'Historical progress tracking for each goal';
COMMENT ON TABLE goal_completions IS 'Detailed completion records and fund collection status';
COMMENT ON TABLE goal_assignments IS 'Assignment of goals to agents and farms';
COMMENT ON TABLE goal_milestones IS 'Intermediate milestones and achievements';
COMMENT ON TABLE goal_analytics IS 'Performance analytics and AI-driven insights';
COMMENT ON TABLE goal_events IS 'Audit trail for all goal-related events';
COMMENT ON TABLE goal_templates IS 'Reusable goal templates for quick goal creation';