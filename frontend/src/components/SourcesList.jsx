import { useState } from 'react'
import './SourcesList.css'

export default function SourcesList({ sources }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="sources">
      <button className="sources-toggle" onClick={() => setOpen(prev => !prev)}>
        {open ? '▾' : '▸'} Sources ({sources.length})
      </button>
      {open && (
        <ul className="sources-list">
          {sources.map((s, i) => (
            <li key={i} className="source-item">
              <span className="source-tool">{s.tool}</span>
              <span className="source-citation">{s.citation}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}