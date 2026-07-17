import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import SourcesList from './SourcesList'
import ToolError from './ToolError'
import './MessageBubble.css'

export default function MessageBubble({ message, isStreaming = false, streamingTool = null, toolErrors = [], reasoningText = '' }) {
  const { role, content, sources, toolsUsed, intent } = message

  if (role === 'user') {
    return (
      <div className="bubble bubble-user">
        <div className="bubble-label">You</div>
        <p className="bubble-text">{content}</p>
      </div>
    )
  }

  return (
    <div className={`bubble bubble-assistant ${isStreaming ? 'is-streaming' : ''}`}>
      <div className="bubble-label">
        TechCorp AI
        {intent && <span className="intent-badge">{intent}</span>}
        {isStreaming && <span className="streaming-indicator" title="AI is generating…" />}
      </div>

      {/* Tool errors */}
      {toolErrors.length > 0 && (
        <div className="tool-errors-list">
          {toolErrors.map((err, i) => (
            <ToolError key={i} tool={err.tool} error={err.message} />
          ))}
        </div>
      )}

      {/* Agent reasoning accordion */}
      {reasoningText && (
        <details className="agent-reasoning">
          <summary>🧠 Agent Reasoning</summary>
          <p>{reasoningText}</p>
        </details>
      )}

      {/* Tool execution progress */}
      {streamingTool && (
        <div className="tool-progress">
          <span className="tool-progress-spinner" />
          <span className="tool-progress-text">
            {_toolLabel(streamingTool)}…
          </span>
          {typeof streamingTool === 'object' && streamingTool.error && (
            <span className="tool-progress-error">{streamingTool.error}</span>
          )}
        </div>
      )}

      {toolsUsed && toolsUsed.length > 0 && (
        <div className="tools-chips">
          {toolsUsed.map(tool => {
            const hasError = toolErrors.some(e => e.tool === tool)
            return (
              <span key={tool} className={`tool-chip${hasError ? ' tool-chip-error' : ''}`}>
                {hasError ? '⚠ ' : ''}{tool}
              </span>
            )
          })}
        </div>
      )}

      <div className="bubble-markdown">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {content || (isStreaming ? '▊' : '')}
        </ReactMarkdown>
      </div>

      {!isStreaming && sources && sources.length > 0 && <SourcesList sources={sources} />}
    </div>
  )
}

function _toolLabel(tool) {
  if (typeof tool === 'object' && tool !== null) {
    return tool.message || _toolLabel(tool.tool)
  }
  const labels = {
    rag_search: 'Searching knowledge base',
    sql_query: 'Querying database',
    python_execute: 'Running Python analysis',
    web_search: 'Searching the web',
    memory: 'Searching memory',
    email: 'Checking email',
    calendar: 'Checking calendar',
  }
  return labels[tool] || (tool ? `Running ${tool}…` : 'Working…')
}