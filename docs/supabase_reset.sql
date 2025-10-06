-- Reset script for Supabase tables and policies
-- Run this BEFORE running supabase_setup.sql

-- Drop existing views first
DROP VIEW IF EXISTS recent_reports_with_llm;
DROP VIEW IF EXISTS recent_reports;
DROP VIEW IF EXISTS llm_usage_stats;

-- Drop existing policies
DROP POLICY IF EXISTS "Allow all operations for authenticated users" ON reports;
DROP POLICY IF EXISTS "Allow read access for anonymous users" ON reports;
DROP POLICY IF EXISTS "Allow all operations for authenticated users on llm_logs" ON llm_logs;
DROP POLICY IF EXISTS "Allow read access for anonymous users on llm_logs" ON llm_logs;

-- Drop existing tables (this will also drop indexes and constraints)
DROP TABLE IF EXISTS llm_logs;
DROP TABLE IF EXISTS reports;

-- Note: After running this script, run supabase_setup.sql to recreate everything