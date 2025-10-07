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
  const [selectedReport, setSelectedReport] = useState<Report | null>(null)

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
            <div 
              key={report.id} 
              className="report-item"
              onClick={() => setSelectedReport(report)}
              style={{ cursor: 'pointer' }}
            >
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

      {selectedReport && (
        <div className="modal-overlay" onClick={() => setSelectedReport(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{selectedReport.project_name}</h3>
              <button className="close-button" onClick={() => setSelectedReport(null)}>×</button>
            </div>
            <div className="modal-meta">
              <span>Date: {new Date(selectedReport.created_at).toLocaleString()}</span>
              {selectedReport.llm_model_used && (
                <span>Model: {selectedReport.llm_model_used}</span>
              )}
              {selectedReport.llm_tokens_used != null && (
                <span>Tokens: {selectedReport.llm_tokens_used}</span>
              )}
            </div>
            <div className="modal-section">
              <h4>Summary</h4>
              {selectedReport.summary?.overview && (
                <p>{selectedReport.summary.overview}</p>
              )}
              {selectedReport.summary?.text && (
                <p>{selectedReport.summary.text}</p>
              )}
              {Array.isArray(selectedReport.summary?.risks) && selectedReport.summary!.risks!.length > 0 && (
                <div>
                  <h5>Risks</h5>
                  <ul>
                    {selectedReport.summary!.risks!.map((risk, i) => (
                      <li key={i}>{risk}</li>
                    ))}
                  </ul>
                </div>
              )}
              {Array.isArray(selectedReport.summary?.recommendations) && selectedReport.summary!.recommendations!.length > 0 && (
                <div>
                  <h5>Recommendations</h5>
                  <ul>
                    {selectedReport.summary!.recommendations!.map((rec, i) => (
                      <li key={i}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            <div className="modal-section">
              <h4>Metrics</h4>
              {(() => {
                const m: any = selectedReport.metrics || {}
                const readability = m.readability || {}
                const python = readability.python || {}
                const js = readability.javascript_typescript || {}
                const reusability = m.reusability || {}
                const robustness = m.robustness || {}
                const robustnessPy = robustness.python || {}
                const performance = m.performance || {}
                return (
                  <div className="modal-metrics-grid">
                    <div className="metric-card">
                      <h5>Readability</h5>
                      <div className="metric-item">README: {readability.has_readme ? '✅' : '❌'}</div>
                      <div className="metric-item">Python Functions: {python.function_count ?? 0}</div>
                      <div className="metric-item">Docstrings: {python.docstring_count ?? 0}</div>
                      <div className="metric-item">Python Comment Density: {typeof python.comment_density === 'number' ? (python.comment_density * 100).toFixed(1) + '%' : '0%'}</div>
                      <div className="metric-item">JS/TS JSDoc Blocks: {js.jsdoc_blocks ?? 0}</div>
                      <div className="metric-item">JS/TS Comment Density: {typeof js.comment_density === 'number' ? (js.comment_density * 100).toFixed(1) + '%' : '0%'}</div>
                    </div>

                    <div className="metric-card">
                      <h5>Reusability</h5>
                      <div className="metric-item">Duplicate Groups: {reusability.duplicate_group_count ?? 0}</div>
                      {Array.isArray(reusability.duplicate_groups) && reusability.duplicate_groups.length > 0 && (
                        <details>
                          <summary>Show duplicate examples</summary>
                          <ul>
                            {reusability.duplicate_groups.slice(0,5).map((grp: string[], idx: number) => (
                              <li key={idx}>{grp.join(' , ')}</li>
                            ))}
                          </ul>
                        </details>
                      )}
                      {reusability.recommendation && (
                        <div className="metric-note">{reusability.recommendation}</div>
                      )}
                    </div>

                    <div className="metric-card">
                      <h5>Robustness</h5>
                      <div className="metric-item">Has Tests: {robustness.has_tests ? '✅' : '❌'}</div>
                      <div className="metric-item">Try/Except Blocks: {robustnessPy.try_except_count ?? 0}</div>
                      <div className="metric-item">Python Functions: {robustnessPy.function_count ?? 0}</div>
                      <div className="metric-item">Typed Function Ratio: {typeof robustnessPy.typed_function_ratio === 'number' ? (robustnessPy.typed_function_ratio * 100).toFixed(1) + '%' : '0%'}</div>
                    </div>

                    <div className="metric-card">
                      <h5>Performance & Risks</h5>
                      <div className="metric-item">SQL Risk Files: {Array.isArray(performance.sql_injection_risk_files) ? performance.sql_injection_risk_files.length : 0}</div>
                      <div className="metric-item">Risky Calls Files: {Array.isArray(performance.risky_calls_files) ? performance.risky_calls_files.length : 0}</div>
                      {performance.notes && (
                        <div className="metric-note">{performance.notes}</div>
                      )}
                      {Array.isArray(performance.sql_injection_risk_files) && performance.sql_injection_risk_files.length > 0 && (
                        <details>
                          <summary>Show SQL risk files</summary>
                          <ul>
                            {performance.sql_injection_risk_files.slice(0,10).map((path: string, i: number) => (
                              <li key={i}>{path}</li>
                            ))}
                          </ul>
                        </details>
                      )}
                      {Array.isArray(performance.risky_calls_files) && performance.risky_calls_files.length > 0 && (
                        <details>
                          <summary>Show risky call files</summary>
                          <ul>
                            {performance.risky_calls_files.slice(0,10).map((path: string, i: number) => (
                              <li key={i}>{path}</li>
                            ))}
                          </ul>
                        </details>
                      )}
                    </div>
                  </div>
                )
              })()}
              <div className="metrics-row">
                <span>Files: {selectedReport.metrics.file_count}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}