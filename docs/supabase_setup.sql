-- Create the reports table for storing codebase evaluation results
DROP TABLE IF EXISTS llm_logs CASCADE;
DROP TABLE IF EXISTS reports CASCADE;
DROP VIEW IF EXISTS recent_reports_with_llm CASCADE;
DROP VIEW IF EXISTS llm_usage_stats CASCADE;

CREATE TABLE reports (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    project_name TEXT NOT NULL,
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

-- Create indexes for better query performance
CREATE INDEX idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX idx_reports_project_name ON reports(project_name);
CREATE INDEX idx_reports_run_id ON reports(run_id);
CREATE INDEX idx_llm_logs_run_id ON llm_logs(run_id);
CREATE INDEX idx_llm_logs_timestamp ON llm_logs(request_timestamp DESC);

-- Enable Row Level Security (RLS) - optional but recommended
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_logs ENABLE ROW LEVEL SECURITY;

-- Create policies for reports table
CREATE POLICY "reports_auth_all" ON reports
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "reports_anon_select" ON reports
    FOR SELECT USING (true);

-- Create policies for llm_logs table
CREATE POLICY "llm_logs_auth_all" ON llm_logs
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "llm_logs_anon_select" ON llm_logs
    FOR SELECT USING (true);

-- Grant necessary permissions
GRANT ALL ON reports TO authenticated;
GRANT SELECT ON reports TO anon;
GRANT ALL ON llm_logs TO authenticated;
GRANT SELECT ON llm_logs TO anon;
GRANT USAGE, SELECT ON SEQUENCE reports_id_seq TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE llm_logs_id_seq TO authenticated;

-- Create a view for recent reports with LLM usage stats
CREATE VIEW recent_reports_with_llm AS
SELECT 
    r.id,
    r.run_id,
    r.project_name,
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

-- Create a view for LLM usage analytics
CREATE VIEW llm_usage_stats AS
SELECT 
    DATE_TRUNC('day', r.created_at) as date,
    COUNT(*) as total_evaluations,
    COUNT(r.llm_request_time) as llm_requests,
    COUNT(r.llm_response_time) as llm_successes,
    COUNT(ll.error_message) as llm_errors,
    AVG(EXTRACT(EPOCH FROM (r.llm_response_time - r.llm_request_time))) as avg_response_time_seconds,
    SUM(r.llm_tokens_used) as total_tokens,
    ARRAY_AGG(DISTINCT r.llm_model_used) FILTER (WHERE r.llm_model_used IS NOT NULL) as models_used
FROM reports r
LEFT JOIN llm_logs ll ON r.id = ll.report_id
WHERE r.created_at >= NOW() - INTERVAL '90 days'
GROUP BY DATE_TRUNC('day', r.created_at)
ORDER BY date DESC;