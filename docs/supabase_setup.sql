-- Create the reports table for storing codebase evaluation results
DROP TABLE IF EXISTS llm_logs CASCADE;
DROP TABLE IF EXISTS reports CASCADE;
DROP VIEW IF EXISTS recent_reports_with_llm CASCADE;
DROP VIEW IF EXISTS llm_usage_stats CASCADE;

CREATE TABLE reports (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    project_name TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    metrics JSONB NOT NULL,
    summary JSONB,
    llm_request_time TIMESTAMPTZ,
    llm_response_time TIMESTAMPTZ,
    llm_tokens_used INTEGER,
    llm_model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create the llm_logs table for tracking OpenAI API usage
CREATE TABLE llm_logs (
    id BIGSERIAL PRIMARY KEY,
    report_id BIGINT REFERENCES reports(id),
    run_id TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    request_timestamp TIMESTAMPTZ DEFAULT NOW(),
    response_timestamp TIMESTAMPTZ,
    model_used TEXT,
    tokens_used INTEGER,
    request_size INTEGER,
    response_size INTEGER,
    success BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    response_data JSONB
);

-- Create user_profiles table for additional user information
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    full_name TEXT,
    avatar_url TEXT,
    subscription_tier TEXT DEFAULT 'free',
    total_evaluations INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX idx_reports_project_name ON reports(project_name);
CREATE INDEX idx_reports_run_id ON reports(run_id);
CREATE INDEX idx_reports_user_id ON reports(user_id);
CREATE INDEX idx_llm_logs_run_id ON llm_logs(run_id);
CREATE INDEX idx_llm_logs_timestamp ON llm_logs(request_timestamp DESC);
CREATE INDEX idx_llm_logs_user_id ON llm_logs(user_id);
CREATE INDEX idx_user_profiles_email ON user_profiles(email);

-- Enable Row Level Security (RLS)
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for reports table
CREATE POLICY "Users can view own reports" ON reports
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own reports" ON reports
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own reports" ON reports
    FOR UPDATE USING (auth.uid() = user_id);

-- Create RLS policies for llm_logs table
CREATE POLICY "Users can view own llm_logs" ON llm_logs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own llm_logs" ON llm_logs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Create RLS policies for user_profiles table
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON user_profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile" ON user_profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Create a view for recent reports with LLM usage stats (user-specific)
CREATE VIEW recent_reports_with_llm AS
SELECT 
    r.id,
    r.run_id,
    r.project_name,
    r.user_id,
    r.created_at,
    (r.metrics->>'file_count')::int as file_count,
    CASE 
        WHEN r.summary IS NOT NULL THEN true 
        ELSE false 
    END as has_summary,
    r.llm_model_used,
    r.llm_tokens_used,
    EXTRACT(EPOCH FROM (r.llm_response_time - r.llm_request_time)) as llm_duration_seconds,
    ll.success as llm_success,
    ll.error_message as llm_error
FROM reports r 
LEFT JOIN llm_logs ll ON r.id = ll.report_id
WHERE r.created_at >= NOW() - INTERVAL '30 days'
ORDER BY r.created_at DESC;

-- Create a view for user statistics
CREATE VIEW user_stats AS
SELECT 
    up.id as user_id,
    up.email,
    up.full_name,
    up.subscription_tier,
    COUNT(r.id) as total_reports,
    SUM(r.llm_tokens_used) as total_tokens,
    AVG((r.metrics->>'file_count')::int) as avg_files_per_report,
    MAX(r.created_at) as last_evaluation,
    COUNT(CASE WHEN r.created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as reports_last_30_days
FROM user_profiles up
LEFT JOIN reports r ON up.id = r.user_id
GROUP BY up.id, up.email, up.full_name, up.subscription_tier;

-- Function to automatically create user profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, email, full_name, avatar_url)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email),
        NEW.raw_user_meta_data->>'avatar_url'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create user profile on signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Function to update user stats
CREATE OR REPLACE FUNCTION public.update_user_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE user_profiles 
    SET 
        total_evaluations = total_evaluations + 1,
        total_tokens_used = total_tokens_used + COALESCE(NEW.llm_tokens_used, 0),
        updated_at = NOW()
    WHERE id = NEW.user_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to update user stats on new report
DROP TRIGGER IF EXISTS on_report_created ON reports;
CREATE TRIGGER on_report_created
    AFTER INSERT ON reports
    FOR EACH ROW EXECUTE FUNCTION public.update_user_stats();