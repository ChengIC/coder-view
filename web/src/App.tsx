import { useEffect, useRef, useState } from 'react'
import type { User } from '@supabase/supabase-js'
import { supabase } from './lib/supabase'
import { Auth } from './components/Auth'
import { Dashboard } from './components/Dashboard'
import { Sidebar } from './components/Sidebar'
import './App.css'

type ReadabilityMetrics = {
  has_readme: boolean
  python: {
    docstring_count: number
    function_count: number
    comment_density: number
  }
  javascript_typescript: {
    jsdoc_blocks: number
    comment_density: number
  }
}

type ReusabilityMetrics = {
  duplicate_group_count: number
  duplicate_groups: string[][]
  recommendation: string
}

type RobustnessMetrics = {
  has_tests: boolean
  python: {
    try_except_count: number
    function_count: number
    typed_function_ratio: number
  }
}

type PerformanceMetrics = {
  sql_injection_risk_files: string[]
  risky_calls_files: string[]
  notes: string
}

type Metrics = {
  readability: ReadabilityMetrics
  reusability: ReusabilityMetrics
  robustness: RobustnessMetrics
  performance: PerformanceMetrics
  file_count: number
}

type Summary = { 
  text?: string
  overview?: string
  risks?: string[]
  recommendations?: string[]
  code_patterns?: string
  architecture_notes?: string
  priority_fixes?: string[]
  error?: string
} | Record<string, unknown>

type Report = {
  run_id: string
  project_name: string
  metrics: Metrics
  summary?: Summary | null
}

type EvaluateResponse = {
  report: Report
  supabase: unknown
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [authToken, setAuthToken] = useState<string | null>(null)
  const [currentView, setCurrentView] = useState<'evaluate' | 'dashboard'>('evaluate')
  const [files, setFiles] = useState<File[]>([])
  const [folderName, setFolderName] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  useEffect(() => {
    // Get auth token when user changes
    if (user) {
      supabase.auth.getSession().then(({ data: { session } }) => {
        setAuthToken(session?.access_token || null)
      })
    } else {
      setAuthToken(null)
    }
  }, [user])

  useEffect(() => {
    // Enable folder selection attributes without TypeScript prop errors
    const el = inputRef.current
    if (el) {
      el.setAttribute('webkitdirectory', '')
      el.setAttribute('directory', '')
      el.setAttribute('multiple', '')
    }
  }, [])

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const list = e.target.files
    if (!list || list.length === 0) {
      setFiles([])
      setFolderName(null)
      return
    }
    const arr = Array.from(list)
    setFiles(arr)
    const first = arr[0] as File & { webkitRelativePath?: string }
    const rel = first.webkitRelativePath || first.name
    const root = rel.split('/')[0] || null
    setFolderName(root)
  }

  const onSubmit = async () => {
    if (!user || !authToken) {
      setError('Please sign in to evaluate code')
      return
    }

    setError(null)
    setReport(null)
    if (!files.length) {
      setError('Please select a folder to upload')
      return
    }
    setLoading(true)
    try {
      const form = new FormData()
      for (const f of files) {
        const ff = f as File & { webkitRelativePath?: string }
        const rel = ff.webkitRelativePath || f.name
        form.append('files', f, rel)
      }
      if (folderName) {
        form.append('project_name', folderName)
      }
      
      const endpoints = [
        `${API_URL}/evaluate`,
        `http://localhost:8001/evaluate`,
      ]
      let lastErr: Error | null = null
      for (const url of endpoints) {
        try {
          const resp = await fetch(url, { 
            method: 'POST', 
            body: form,
            headers: {
              'Authorization': `Bearer ${authToken}`
            }
          })
          if (!resp.ok) {
            const msg = await resp.text()
            throw new Error(msg || `Request failed: ${resp.status}`)
          }
          const data = (await resp.json()) as EvaluateResponse
          setReport(data.report)
          lastErr = null
          break
        } catch (err) {
          lastErr = err as Error
        }
      }
      if (lastErr) throw lastErr
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    setUser(null)
    setAuthToken(null)
    setCurrentView('evaluate')
    setReport(null)
    setFiles([])
    setFolderName(null)
  }

  if (!user) {
    return <Auth onAuthChange={setUser} />
  }

  return (
    <div className="app">
      <Sidebar 
        user={user}
        currentView={currentView}
        sidebarCollapsed={sidebarCollapsed}
        onViewChange={setCurrentView}
        onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
        onSignOut={handleSignOut}
      />

      <main className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        {currentView === 'dashboard' ? (
          <Dashboard user={user} authToken={authToken || ''} />
        ) : (
          <div className="evaluate-page">
            <div className="page-header">
              <h1>Evaluate Codebase</h1>
              <p>Upload a folder to generate a comprehensive code quality report.</p>
            </div>

            <div className="upload-section">
              <div className="upload-card">
                <h3>Select Project Folder</h3>
                <div className="upload-area">
                  <input ref={inputRef} type="file" onChange={onFileChange} />
                  <button 
                    className="upload-btn" 
                    onClick={onSubmit} 
                    disabled={loading || files.length === 0}
                  >
                    {loading ? 'Evaluating…' : 'Start Evaluation'}
                  </button>
                </div>
                
                {files.length > 0 && (
                  <div className="upload-info">
                    <p><strong>Selected:</strong> {folderName ?? 'unknown'}</p>
                    <p><strong>Files:</strong> {files.length}</p>
                  </div>
                )}
                
                {error && <div className="error-message">{error}</div>}
              </div>
            </div>

            {report && (
              <div className="results-section">
                <div className="results-header">
                  <h2>Evaluation Results</h2>
                  <div className="results-meta">
                    <span>Project: {report.project_name}</span>
                    <span>Files: {report.metrics.file_count}</span>
                  </div>
                </div>
                
                <div className="results-grid">
                  <div className="result-card summary-card">
                    <h3>AI Summary</h3>
                    <div className="summary-content">
                       {report.summary && typeof report.summary === 'object' && 'overview' in report.summary ? (
                         <div>
                           <p><strong>Overview:</strong> {String(report.summary.overview)}</p>
                           {Array.isArray(report.summary.risks) && report.summary.risks.length > 0 && (
                             <div>
                               <p><strong>Key Risks:</strong></p>
                               <ul>
                                 {report.summary.risks.map((risk: string, i: number) => (
                                   <li key={i}>{risk}</li>
                                 ))}
                               </ul>
                             </div>
                           )}
                           {Array.isArray(report.summary.recommendations) && report.summary.recommendations.length > 0 && (
                             <div>
                               <p><strong>Recommendations:</strong></p>
                               <ul>
                                 {report.summary.recommendations.map((rec: string, i: number) => (
                                   <li key={i}>{rec}</li>
                                 ))}
                               </ul>
                             </div>
                           )}
                         </div>
                       ) : (
                         <pre>{JSON.stringify(report.summary ?? { text: 'No summary available' }, null, 2)}</pre>
                       )}
                     </div>
                  </div>
                  
                  <div className="result-card">
                    <h3>📚 Readability</h3>
                    <div className="metric-content">
                      <div className="metric-item">
                        <span>README: {report.metrics.readability.has_readme ? '✅' : '❌'}</span>
                      </div>
                      <div className="metric-item">
                        <span>Python Functions: {report.metrics.readability.python.function_count}</span>
                      </div>
                      <div className="metric-item">
                        <span>Docstrings: {report.metrics.readability.python.docstring_count}</span>
                      </div>
                      <div className="metric-item">
                        <span>Comment Density: {(report.metrics.readability.python.comment_density * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="result-card">
                    <h3>♻️ Reusability</h3>
                    <div className="metric-content">
                      <div className="metric-item">
                        <span>Duplicate Groups: {report.metrics.reusability.duplicate_group_count}</span>
                      </div>
                      <p className="recommendation">{report.metrics.reusability.recommendation}</p>
                    </div>
                  </div>
                  
                  <div className="result-card">
                    <h3>🛡️ Robustness</h3>
                    <div className="metric-content">
                      <div className="metric-item">
                        <span>Has Tests: {report.metrics.robustness.has_tests ? '✅' : '❌'}</span>
                      </div>
                      <div className="metric-item">
                        <span>Try/Except Blocks: {report.metrics.robustness.python.try_except_count}</span>
                      </div>
                      <div className="metric-item">
                        <span>Type Hints: {(report.metrics.robustness.python.typed_function_ratio * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="result-card">
                    <h3>⚡ Performance</h3>
                    <div className="metric-content">
                      <div className="metric-item">
                        <span>SQL Risk Files: {report.metrics.performance.sql_injection_risk_files.length}</span>
                      </div>
                      <div className="metric-item">
                        <span>Risky Calls: {report.metrics.performance.risky_calls_files.length}</span>
                      </div>
                      <p className="recommendation">{report.metrics.performance.notes}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
