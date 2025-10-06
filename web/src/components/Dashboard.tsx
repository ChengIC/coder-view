import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts'
import { Calendar, FileText, Zap, AlertTriangle } from 'lucide-react'
import type { User } from '@supabase/supabase-js'
import type { Report } from '../lib/supabase'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface DashboardProps {
  user: User
  authToken: string
}

interface ChartData {
  date: string
  evaluations: number
  tokens: number
  files: number
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']

export function Dashboard(props: DashboardProps) {
  const { authToken } = props
  // user is available for future features like personalized greetings
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchReports()
  }, [authToken])

  const fetchReports = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_URL}/reports/history?limit=50`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })
      
      if (!response.ok) {
        throw new Error('Failed to fetch reports')
      }
      
      const data = await response.json()
      setReports(data.data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reports')
    } finally {
      setLoading(false)
    }
  }

  // Prepare chart data
  const chartData: ChartData[] = reports.reduce((acc: ChartData[], report) => {
    const date = new Date(report.created_at).toLocaleDateString()
    const existing = acc.find(item => item.date === date)
    
    if (existing) {
      existing.evaluations += 1
      existing.tokens += report.llm_tokens_used || 0
      existing.files += report.metrics.file_count || 0
    } else {
      acc.push({
        date,
        evaluations: 1,
        tokens: report.llm_tokens_used || 0,
        files: report.metrics.file_count || 0
      })
    }
    
    return acc
  }, []).slice(-14) // Last 14 days

  // Calculate stats
  const totalEvaluations = reports.length
  const totalTokens = reports.reduce((sum, r) => sum + (r.llm_tokens_used || 0), 0)
  const totalFiles = reports.reduce((sum, r) => sum + (r.metrics.file_count || 0), 0)
  const avgFilesPerProject = totalFiles / totalEvaluations || 0

  // Project distribution data
  const projectData = reports.reduce((acc: Record<string, number>, report) => {
    acc[report.project_name] = (acc[report.project_name] || 0) + 1
    return acc
  }, {})

  const pieData = Object.entries(projectData).map(([name, count]) => ({
    name: name.length > 15 ? name.substring(0, 15) + '...' : name,
    value: count
  })).slice(0, 5) // Top 5 projects

  if (loading) {
    return <div className="loading">Loading dashboard...</div>
  }

  if (error) {
    return <div className="error">Error: {error}</div>
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Analytics Dashboard</h1>
        <p>Track your code evaluation history and usage statistics</p>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">
            <FileText size={24} />
          </div>
          <div className="stat-content">
            <h3>{totalEvaluations}</h3>
            <p>Total Evaluations</p>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon">
            <Zap size={24} />
          </div>
          <div className="stat-content">
            <h3>{totalTokens.toLocaleString()}</h3>
            <p>Tokens Used</p>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon">
            <Calendar size={24} />
          </div>
          <div className="stat-content">
            <h3>{Math.round(avgFilesPerProject)}</h3>
            <p>Avg Files/Project</p>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon">
            <AlertTriangle size={24} />
          </div>
          <div className="stat-content">
            <h3>{reports.filter(r => r.summary?.risks && Array.isArray(r.summary.risks) && r.summary.risks.length > 0).length}</h3>
            <p>Projects with Risks</p>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="charts-grid">
        <div className="chart-card">
          <h3>Evaluation Activity (Last 14 Days)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="evaluations" stroke="#8884d8" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Token Usage Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="tokens" fill="#82ca9d" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Project Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}-${entry.name}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Reports */}
      <div className="recent-reports">
        <h3>Recent Evaluations</h3>
        <div className="reports-list">
          {reports.slice(0, 10).map((report) => (
            <div key={report.id} className="report-item">
              <div className="report-header">
                <h4>{report.project_name}</h4>
                <span className="report-date">
                  {new Date(report.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="report-stats">
                <span>{report.metrics.file_count} files</span>
                {report.llm_tokens_used && (
                  <span>{report.llm_tokens_used} tokens</span>
                )}
                {report.summary && typeof report.summary === 'object' && 'risks' in report.summary && Array.isArray(report.summary.risks) && (
                  <span className="risks">{report.summary.risks.length} risks</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}