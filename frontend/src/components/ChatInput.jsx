import { useState, useEffect, useRef } from 'react'
import { Globe, BookOpenText, Database, Code2, Brain, FileText, Plus, X } from 'lucide-react'
import './ChatInput.css'

const TOOL_MENU = [
  { name: 'web_search',      label: 'Web Search',        icon: Globe },
  { name: 'rag_search',      label: 'Knowledge Base',    icon: BookOpenText },
  { name: 'sql_query',       label: 'Database',          icon: Database },
  { name: 'python_execute',  label: 'Python Analysis',   icon: Code2 },
  { name: 'memory',          label: 'Memory',            icon: Brain },
  { name: 'report_generator',label: 'Report',            icon: FileText },
]

export default function ChatInput({ onSend, disabled, prefill, onPrefillConsumed }) {
  const [text, setText] = useState('')
  const [selectedTool, setSelectedTool] = useState(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  // Close on outside click + Escape
  useEffect(() => {
    if (!menuOpen) return
    const close = (e) => {
      if (e.type === 'keydown') { if (e.key === 'Escape') setMenuOpen(false) }
      else if (e.type === 'mousedown' && menuRef.current) {
        if (!menuRef.current.contains(e.target)) setMenuOpen(false)
      }
    }
    window.addEventListener('mousedown', close)
    window.addEventListener('keydown', close)
    return () => { window.removeEventListener('mousedown', close); window.removeEventListener('keydown', close) }
  }, [menuOpen])

  useEffect(() => {
    if (prefill) {
      setText(prefill)
      onPrefillConsumed?.()
    }
  }, [prefill])

  function handleSubmit() {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed, selectedTool?.name || null)
    setText('')
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const ActiveIcon = selectedTool?.icon || null

  return (
    <div className="chat-input-bar">
      <div className="tool-picker-wrapper" ref={menuRef}>
        <button
          className={`tool-picker-btn${selectedTool ? ' active' : ''}${menuOpen ? ' open' : ''}`}
          disabled={disabled}
          onClick={() => setMenuOpen(v => !v)}
          title="Select tool"
        >
          {selectedTool ? <ActiveIcon size={16} /> : <Plus size={16} />}
        </button>
        {menuOpen && (
          <div className="tool-picker-menu">
            {TOOL_MENU.map(t => {
              const Icon = t.icon
              return (
                <button key={t.name} className="tool-picker-item" onClick={() => { setSelectedTool(t); setMenuOpen(false) }}>
                  <Icon size={15} /> <span>{t.label}</span>
                </button>
              )
            })}
          </div>
        )}
      </div>

      <textarea
        className="chat-input"
        value={text}
        onChange={e => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask the AI employee anything..."
        rows={2}
        disabled={disabled}
      />

      {selectedTool && (
        <div className="tool-chip">
          <ActiveIcon size={13} />
          <span>{selectedTool.label}</span>
          <button className="tool-chip-x" onClick={() => setSelectedTool(null)} title="Clear tool selection"><X size={12} /></button>
        </div>
      )}

      <button
        className="send-button"
        onClick={handleSubmit}
        disabled={disabled || !text.trim()}
      >
        Send
      </button>
    </div>
  )
}