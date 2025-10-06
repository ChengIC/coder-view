import { useEffect, useRef, useState } from 'react'
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

type Summary = { text?: string } | Record<string, unknown>

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
  const [files, setFiles] = useState<File[]>([])
  const [folderName, setFolderName] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<Report | null>(null)

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
      const resp = await fetch(`${API_URL}/evaluate`, {
        method: 'POST',
        body: form,
      })
      if (!resp.ok) {
        const msg = await resp.text()
        throw new Error(msg || 'Request failed')
      }
      const data = (await resp.json()) as EvaluateResponse
      setReport(data.report)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <header>
        <h1>Codebase Evaluator</h1>
        <p>Upload a zip of your repository’s parent directory to generate a report.</p>
      </header>

      <section className="uploader">
        <input ref={inputRef} type="file" onChange={onFileChange} />
        <button onClick={onSubmit} disabled={loading || files.length === 0}>
          {loading ? 'Evaluating…' : 'Evaluate'}
        </button>
        {error && <p className="error">{error}</p>}
        {files.length > 0 && (
          <p>
            Selected folder: <code>{folderName ?? 'unknown'}</code> • Files: {files.length}
          </p>
        )}
      </section>

      {report && (
        <section className="report">
          <h2>Report</h2>
          <div className="report-grid">
            <div className="card">
              <h3>Summary</h3>
              <pre>{JSON.stringify(report.summary ?? { text: 'No summary (LLM disabled)' }, null, 2)}</pre>
            </div>
            <div className="card">
              <h3>Readability</h3>
              <pre>{JSON.stringify(report.metrics.readability, null, 2)}</pre>
            </div>
            <div className="card">
              <h3>Reusability</h3>
              <pre>{JSON.stringify(report.metrics.reusability, null, 2)}</pre>
            </div>
            <div className="card">
              <h3>Robustness</h3>
              <pre>{JSON.stringify(report.metrics.robustness, null, 2)}</pre>
            </div>
            <div className="card">
              <h3>Performance</h3>
              <pre>{JSON.stringify(report.metrics.performance, null, 2)}</pre>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}

export default App
