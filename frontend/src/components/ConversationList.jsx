import { useState, useEffect } from 'react'
import { fetchConversations, createConversation, deleteConversation } from '../hooks/useApi'
import './ConversationList.css'

export default function ConversationList({ activeId, onSelect, onNew, refreshKey }) {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [collapsed, setCollapsed] = useState(true)

  useEffect(() => {
    loadConversations()
  }, [])

  // Reload when parent triggers refresh (e.g., new conversation auto-created)
  useEffect(() => {
    if (refreshKey) loadConversations()
  }, [refreshKey])

  async function loadConversations() {
    try {
      setLoading(true)
      setError(null)
      const list = await fetchConversations()
      setConversations(list)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleNew() {
    try {
      const conv = await createConversation()
      setConversations(prev => [{
        id: conv.id,
        title: 'New Chat',
        message_count: 0,
        updated_at: new Date().toISOString(),
      }, ...prev])
      onNew?.(conv.id)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleDelete(e, convId) {
    e.stopPropagation()
    try {
      await deleteConversation(convId)
      setConversations(prev => prev.filter(c => c.id !== convId))
      if (convId === activeId) {
        onNew?.(null)
      }
    } catch (err) {
      setError(err.message)
    }
  }

  function formatDate(isoString) {
    const d = new Date(isoString)
    const now = new Date()
    const diffMs = now - d
    const diffHrs = diffMs / (1000 * 60 * 60)

    if (diffHrs < 24) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } else if (diffHrs < 168) {
      return d.toLocaleDateString([], { weekday: 'short' })
    } else {
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
    }
  }

  const filtered = conversations.filter(c =>
    c.title.toLowerCase().includes(search.toLowerCase())
  )

  if (collapsed) {
    return (
      <div
        className="conversation-list collapsed"
        onClick={() => setCollapsed(false)}
        title="Expand conversations"
      >
        <span className="conv-expand-chevron">▶</span>
      </div>
    )
  }

  return (
    <div className="conversation-list">
      <div className="conv-header">
        <button className="conv-new-btn" onClick={handleNew}>
          + New Chat
        </button>
        <button
          className="conv-collapse-btn"
          onClick={() => setCollapsed(true)}
          title="Collapse conversations"
        >
          ◀
        </button>
      </div>

      <div className="conv-search-wrap">
        <span className="conv-search-icon">🔍</span>
        <input
          className="conv-search"
          type="text"
          placeholder="Search conversations..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {error && (
        <div className="conv-error">
          {error}
          <button onClick={loadConversations}>Retry</button>
        </div>
      )}

      <div className="conv-items">
        {loading && conversations.length === 0 && (
          <div className="conv-empty">Loading…</div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="conv-empty">No conversations found</div>
        )}

        {filtered.map(conv => (
          <div
            key={conv.id}
            className={`conv-item ${conv.id === activeId ? 'active' : ''}`}
            onClick={() => onSelect(conv.id)}
          >
            <div className="conv-avatar">{conv.title.charAt(0).toUpperCase()}</div>
            <div className="conv-item-content">
              <span className="conv-title">{conv.title}</span>
              <span className="conv-preview">
                {conv.message_count > 0 ? `${conv.message_count} messages` : 'No messages'}
              </span>
              <span className="conv-meta">
                <span className="conv-date">{formatDate(conv.updated_at)}</span>
              </span>
            </div>
            <button
              className="conv-delete-btn"
              onClick={(e) => handleDelete(e, conv.id)}
              title="Delete conversation"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}