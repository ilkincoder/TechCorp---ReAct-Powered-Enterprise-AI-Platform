import './ExecutionGraph.css'

const TOOL_ICONS = {
  rag_search: '📚',
  sql_query: '📊',
  python_execute: '🐍',
  web_search: '🌐',
  memory: '🧠',
  email: '📧',
  calendar: '📅',
}

const TOOL_LABELS = {
  rag_search: 'Knowledge Base',
  sql_query: 'SQL Query',
  python_execute: 'Python',
  web_search: 'Web Search',
  memory: 'Memory',
  email: 'Email',
  calendar: 'Calendar',
}

const STATUS_LABELS = {
  pending: '○',
  running: '◉',
  success: '✔',
  failed: '✖',
  retrying: '↻',
  skipped: '—',
}

export default function ExecutionGraph({ steps, isStreaming, intent, reasoning }) {
  if (!steps || steps.length === 0) return null

  return (
    <div className="execution-graph">
      {/* Planner node */}
      <div className="graph-node graph-planner">
        <div className="graph-node-icon">🧠</div>
        <div className="graph-node-content">
          <div className="graph-node-label">Planner</div>
          {intent && <div className="graph-node-detail">{intent}</div>}
        </div>
      </div>

      {/* Connector */}
      <div className="graph-connector">
        <div className="graph-line" />
      </div>

      {/* Tool nodes */}
      <div className="graph-tools-row">
        {steps.map((step, i) => (
          <div key={`${step.tool}-${i}`} className="graph-tool-wrapper">
            <div className={`graph-node graph-tool status-${step.status}`}>
              <div className="graph-node-icon">
                {step.status === 'running' && isStreaming ? (
                  <span className="graph-spinner" />
                ) : (
                  TOOL_ICONS[step.tool] || '🔧'
                )}
              </div>
              <div className="graph-node-content">
                <div className="graph-node-label">
                  {TOOL_LABELS[step.tool] || step.tool}
                  <span className={`graph-status-icon status-${step.status}`}>
                    {STATUS_LABELS[step.status] || '○'}
                  </span>
                </div>
                {step.goal && (
                  <div className="graph-node-detail" title={step.goal}>
                    {step.goal}
                  </div>
                )}
                {step.executionTimeMs != null && (
                  <div className="graph-node-timing">{step.executionTimeMs}ms</div>
                )}
                {step.error && step.status === 'failed' && (
                  <div className="graph-node-error">{step.error}</div>
                )}
              </div>
            </div>
            {i < steps.length - 1 && <div className="graph-tool-arrow">→</div>}
          </div>
        ))}
      </div>

      {/* Connector to answer */}
      <div className="graph-connector">
        <div className="graph-line" />
      </div>

      {/* Answer node */}
      <div className={`graph-node graph-answer ${isStreaming ? 'status-running' : ''}`}>
        <div className="graph-node-icon">💬</div>
        <div className="graph-node-content">
          <div className="graph-node-label">
            Final Answer
            {isStreaming && <span className="graph-pulse" />}
          </div>
        </div>
      </div>
    </div>
  )
}
