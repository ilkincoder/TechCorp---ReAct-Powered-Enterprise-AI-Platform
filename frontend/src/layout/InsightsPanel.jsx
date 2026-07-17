import { useState } from 'react'
import { useQuery } from '../context/QueryContext'
import SourcesList from '../components/SourcesList'
import ExecutionGraph from '../components/ExecutionGraph'
import './InsightsPanel.css'

const TABS = ['Overview', 'Sources', 'Timeline', 'Details']

export default function InsightsPanel({ collapsed, onCollapseChange }) {
  const { isQuerying, lastResult, latency, planSteps, toolErrors, validationWarnings } = useQuery()
  const [activeTab, setActiveTab] = useState('Overview')

  if (collapsed) {
    return (
      <aside
        className="insights-panel collapsed"
        onClick={() => onCollapseChange(false)}
        title="Expand insights"
      >
        <span className="insights-expand-chevron">◀</span>
      </aside>
    )
  }

  return (
    <aside className="insights-panel">
      <div className="insights-header">
        <h3>Insights</h3>
        <button
          className="insights-collapse-btn"
          onClick={() => onCollapseChange(true)}
          title="Collapse insights"
        >
          ▶
        </button>
      </div>

      {!lastResult && !isQuerying && (
        <div className="insights-empty">
          <p>Run a query in Chat to see AI reasoning transparency here.</p>
        </div>
      )}

      {isQuerying && (
        <div className="insights-loading">
          <div className="insights-pulse" />
          <p>Processing…</p>
        </div>
      )}

      {lastResult && (
        <>
          <div className="insights-tabs">
            {TABS.map(tab => (
              <button
                key={tab}
                className={`insights-tab ${activeTab === tab ? 'active' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </div>

          {activeTab === 'Overview' && (
            <div className="insights-stats-grid">
              <div className="insight-stat-card accent-primary">
                <span className="stat-value">{lastResult.sources.length}</span>
                <span className="stat-label">Sources Found</span>
              </div>
              <div className="insight-stat-card accent-success">
                <span className="stat-value">{lastResult.toolsUsed.length}</span>
                <span className="stat-label">Tools Executed</span>
              </div>
              <div className="insight-stat-card accent-info">
                <span className="stat-value">{latency != null ? `${latency.toFixed(1)}s` : '—'}</span>
                <span className="stat-label">Latency</span>
              </div>
              {toolErrors.length > 0 && (
                <div className="insight-stat-card accent-danger">
                  <span className="stat-value">{toolErrors.length}</span>
                  <span className="stat-label">Error{toolErrors.length > 1 ? 's' : ''}</span>
                </div>
              )}
              {validationWarnings.length > 0 && (
                <div className="insight-stat-card accent-warning">
                  <span className="stat-value">{validationWarnings.length}</span>
                  <span className="stat-label">Warning{validationWarnings.length > 1 ? 's' : ''}</span>
                </div>
              )}
            </div>
          )}

          {activeTab === 'Sources' && (
            <div className="insights-sections">
              <section className="insight-section">
                <h4>Sources</h4>
                {lastResult.sources.length > 0 ? (
                  <SourcesList sources={lastResult.sources} />
                ) : (
                  <p className="muted">—</p>
                )}
              </section>
            </div>
          )}

          {activeTab === 'Timeline' && (
            <div className="insights-sections">
              <ExecutionGraph
                steps={planSteps}
                isStreaming={isQuerying}
                intent={lastResult.intent}
                reasoning=""
              />
              {planSteps.length === 0 && !isQuerying && (
                <p className="muted" style={{ padding: '12px 16px' }}>
                  No execution data available for this query.
                </p>
              )}
            </div>
          )}

          {activeTab === 'Details' && (
            <div className="insights-sections">
              <section className="insight-section">
                <h4>Intent</h4>
                <p className="insight-value">{lastResult.intent || '—'}</p>
              </section>

              <section className="insight-section">
                <h4>Tools Used</h4>
                <ul className="insight-checklist">
                  {lastResult.toolsUsed.map(tool => {
                    const hasError = toolErrors.some(e => e.tool === tool)
                    return (
                      <li key={tool} className={hasError ? 'tool-item-error' : ''}>
                        {hasError ? '✖' : '✓'} {tool}
                      </li>
                    )
                  })}
                  {lastResult.toolsUsed.length === 0 && <li className="muted">—</li>}
                </ul>
              </section>

              {toolErrors.length > 0 && (
                <section className="insight-section">
                  <h4>Errors</h4>
                  {toolErrors.map((err, i) => (
                    <div key={i} className="insight-error-item">
                      <strong>{err.tool}</strong>: {err.message}
                    </div>
                  ))}
                </section>
              )}

              {validationWarnings.length > 0 && (
                <section className="insight-section">
                  <h4>Warnings</h4>
                  {validationWarnings.map((w, i) => (
                    <div key={i} className="insight-warning-item">⚠ {w}</div>
                  ))}
                </section>
              )}

              <section className="insight-section">
                <h4>Latency</h4>
                <p className="insight-value latency-value">
                  {latency != null ? `${latency.toFixed(1)}s` : '—'}
                </p>
              </section>
            </div>
          )}
        </>
      )}
    </aside>
  )
}