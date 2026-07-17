import { useState, useEffect } from 'react'
import './Reports.css'

const API_BASE = 'http://localhost:8000'

export default function Reports() {
  const [reports, setReports] = useState([])
  const [expandedId, setExpandedId] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadReports()
    const interval = setInterval(loadReports, 10000)
    return () => clearInterval(interval)
  }, [])

  async function loadReports() {
    try {
      const res = await fetch(`${API_BASE}/reports`)
      if (!res.ok) throw new Error(`Failed: ${res.status}`)
      const data = await res.json()
      setReports(data.reports || [])
    } catch (e) {
      console.error('Reports load failed:', e)
    } finally {
      setLoading(false)
    }
  }

  const completed = reports.filter(r => r.status === 'completed')
  const pending = reports.filter(r => r.status !== 'completed')

  return (
    <div className="reports-page">
      <header className="reports-page-header">
        <h2>Reports</h2>
        <span className="reports-page-subtitle">
          {completed.length} report{completed.length !== 1 ? 's' : ''} generated
        </span>
      </header>

      <div className="reports-page-body">
        {loading && (
          <div className="reports-loading">Loading reports…</div>
        )}

        {!loading && completed.length === 0 && (
          <div className="reports-empty-state">
            <span className="reports-empty-icon">📄</span>
            <h3>No reports yet</h3>
            <p>Ask the AI to generate a report in Chat — they'll appear here.</p>
          </div>
        )}

        {pending.length > 0 && (
          <div className="reports-pending-section">
            <h4 className="reports-section-title">Generating…</h4>
            {pending.map(r => (
              <div key={r.id} className="report-card-pending">
                <span className="report-badge pending">{r.status}</span>
                <span>{r.title}</span>
              </div>
            ))}
          </div>
        )}

        {completed.map(r => (
          <div
            key={r.id}
            className={`report-card-full ${expandedId === r.id ? 'expanded' : ''}`}
          >
            <div
              className="report-card-full-header"
              onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}
            >
              <span className="report-badge done">done</span>
              <span className="report-card-full-title">{r.title}</span>
              <span className="report-card-full-date">
                {new Date(r.created_at).toLocaleDateString(undefined, {
                  month: 'short', day: 'numeric', year: 'numeric',
                })}
              </span>
            </div>
            {expandedId === r.id && (
              <div className="report-card-full-content">
                {r.content ? (
                  <div
                    className="report-markdown"
                    dangerouslySetInnerHTML={{ __html: formatMarkdown(r.content) }}
                  />
                ) : (
                  <em>No content available.</em>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function formatMarkdown(text) {
  let html = text
    .replace(/^### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^## (.+)$/gm, '<h3>$1</h3>')
    .replace(/^# (.+)$/gm, '<h2>$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br/>')
  html = '<p>' + html + '</p>'
  html = html.replace(/(<li>.*?<\/li>(?:<br\/>)?)+/g, (match) => {
    const items = match.replace(/<br\/>/g, '')
    return '<ul>' + items + '</ul>'
  })
  return html
}