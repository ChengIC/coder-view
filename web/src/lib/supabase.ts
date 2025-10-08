import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase config: set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY')
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

export interface ReportMetrics {
  readability: Record<string, unknown>
  reusability: Record<string, unknown>
  robustness: Record<string, unknown>
  performance: Record<string, unknown>
  file_count: number
}

export interface ReportSummary {
  overview?: string
  risks?: string[]
  recommendations?: string[]
  code_patterns?: string
  architecture_notes?: string
  priority_fixes?: string[]
  text?: string
  error?: string
}

export interface Report {
  id: number
  run_id: string
  project_name: string
  user_id: string
  metrics: ReportMetrics
  summary: ReportSummary | null
  llm_request_time: string | null
  llm_response_time: string | null
  llm_tokens_used: number | null
  llm_model_used: string | null
  created_at: string
}

export interface UserProfile {
  id: string
  email: string | null
  full_name: string | null
  avatar_url: string | null
  subscription_tier: string
  total_evaluations: number
  total_tokens_used: number
  created_at: string
  updated_at: string
}