# Database Schemas for Cival Dashboard - Python AI Services

This document outlines the SQL DDL for key tables used by the Python AI services, primarily stored in Supabase (PostgreSQL).

## `agent_tasks` Table

Stores records of tasks executed by AI crews or individual agents. It tracks the status, inputs, outputs, errors, and basic logging for each task run.

```sql
-- Ensure the uuid-ossp extension is enabled in your Supabase project
-- if you haven't already (e.g., via the Supabase dashboard SQL editor or a migration).
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Optional: Create an ENUM type for task_status for better data integrity at the DB level.
-- This ensures that the 'status' column can only contain these predefined values.
-- CREATE TYPE public.task_status_enum AS ENUM (
--     'PENDING',
--     'RUNNING',
--     'COMPLETED',
--     'FAILED'
-- );

CREATE TABLE public.agent_tasks (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crew_id TEXT NOT NULL,
    -- If using the ENUM type defined above:
    -- status public.task_status_enum NOT NULL DEFAULT 'PENDING'::public.task_status_enum,
    -- If using TEXT for status (ensure application layer validates against TaskStatus enum):
    status TEXT NOT NULL DEFAULT 'PENDING',
    start_time TIMESTAMP WITH TIME ZONE DEFAULT now(),
    end_time TIMESTAMP WITH TIME ZONE,
    inputs JSONB, -- Stores the initial inputs provided to the crew/task
    output JSONB, -- Stores the final structured result/output from the crew/task
    error_message TEXT, -- Stores any error message if the task failed
    logs_summary JSONB, -- Optional: Can store a list of key log entries or structured event summaries
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Indexes for frequently queried columns
CREATE INDEX idx_agent_tasks_crew_id ON public.agent_tasks(crew_id);
CREATE INDEX idx_agent_tasks_status ON public.agent_tasks(status);
CREATE INDEX idx_agent_tasks_start_time ON public.agent_tasks(start_time DESC);
CREATE INDEX idx_agent_tasks_created_at ON public.agent_tasks(created_at DESC);

-- Trigger for automatically updating the updated_at timestamp on any row modification.
-- This assumes the function `public.handle_updated_at()` has already been created
-- (e.g., from the setup for the `agent_states` table or a general utility functions migration).
-- If not, you would need to create it:
--
-- CREATE OR REPLACE FUNCTION public.handle_updated_at()
-- RETURNS TRIGGER AS $$
-- BEGIN
--   NEW.updated_at = now();
--   RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;

CREATE TRIGGER handle_agent_tasks_updated_at
    BEFORE UPDATE ON public.agent_tasks
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- Enable Row Level Security (RLS) - always a good practice
ALTER TABLE public.agent_tasks ENABLE ROW LEVEL SECURITY;

-- Define RLS policies as needed. For backend services, often a service_role policy is used.
-- Example: Allow full access for users with 'service_role'.
-- CREATE POLICY "Allow full access to service_role"
--     ON public.agent_tasks FOR ALL
--     USING (auth.role() = 'service_role')
--     WITH CHECK (auth.role() = 'service_role');

-- Example: If tasks are user-specific and you have a user_id column:
-- ALTER TABLE public.agent_tasks ADD COLUMN user_id UUID;
-- CREATE POLICY "Users can manage their own tasks"
--     ON public.agent_tasks FOR ALL
--     USING (auth.uid() = user_id)
--     WITH CHECK (auth.uid() = user_id);

-- For now, a permissive policy if user context isn't integrated at this table level yet:
CREATE POLICY "Allow all access for authenticated users"
    ON public.agent_tasks FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');
-- Or, if service role is the primary interactor:
-- CREATE POLICY "Allow service_role full access" ON public.agent_tasks
-- FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');


-- Comments on table and columns for better schema understanding
COMMENT ON TABLE public.agent_tasks IS 'Stores records of tasks executed by AI crews or agents, including their status, inputs, outputs, errors, and summary logs.';
COMMENT ON COLUMN public.agent_tasks.task_id IS 'Unique identifier for this specific task run (UUID).';
COMMENT ON COLUMN public.agent_tasks.crew_id IS 'Identifier for the crew or agent definition responsible for this task (e.g., "trading_analysis_crew").';
COMMENT ON COLUMN public.agent_tasks.status IS 'Current status of the task. Valid values: PENDING, RUNNING, COMPLETED, FAILED.';
COMMENT ON COLUMN public.agent_tasks.start_time IS 'Timestamp when the task processing began.';
COMMENT ON COLUMN public.agent_tasks.end_time IS 'Timestamp when the task processing concluded (either COMPLETED or FAILED).';
COMMENT ON COLUMN public.agent_tasks.inputs IS 'JSONB object storing the initial input parameters provided to the task/crew.';
COMMENT ON COLUMN public.agent_tasks.output IS 'JSONB object storing the final result or output produced by the task/crew upon successful completion.';
COMMENT ON COLUMN public.agent_tasks.error_message IS 'Text field to store error messages if the task failed.';
COMMENT ON COLUMN public.agent_tasks.logs_summary IS 'JSONB array or object to store a summary of key log entries, events, or intermediate agent outputs generated during the task execution.';
COMMENT ON COLUMN public.agent_tasks.created_at IS 'Timestamp of when the task record was created in the database.';
COMMENT ON COLUMN public.agent_tasks.updated_at IS 'Timestamp of when the task record was last updated in the database.';

```

*(Note: The document will eventually contain other schemas like `agent_states` and `agent_memories`. For this subtask, only `agent_tasks` DDL is added under the main title).*
