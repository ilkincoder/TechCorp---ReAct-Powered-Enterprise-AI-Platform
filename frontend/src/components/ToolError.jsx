import './ToolError.css'

export default function ToolError({ tool, error, onDismiss }) {
  if (!error) return null

  const labels = {
    sql_query: 'SQL',
    rag_search: 'Search',
    python_execute: 'Python',
    web_search: 'Web',
    memory: 'Memory',
    planner: 'Planner',
  }

  return (
    <div className="tool-error">
      <span className="tool-error-icon">⚠</span>
      <span className="tool-error-tool">{labels[tool] || tool}</span>
      <span className="tool-error-msg">{error}</span>
      {onDismiss && (
        <button className="tool-error-dismiss" onClick={onDismiss} title="Dismiss">
          ×
        </button>
      )}
    </div>
  )
}
