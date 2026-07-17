import { useState } from 'react'
import { useRole } from '../context/RoleContext'
import { useTheme } from '../context/ThemeContext'
import './SessionSetup.css'

const ROLES = [
  {
    id: 'engineering_admin',
    label: 'Engineering Admin',
    icon: '⚙',
    description: 'Full access to all tables and departments',
  },
  {
    id: 'sales_intern',
    label: 'Sales Intern',
    icon: '📊',
    description: 'Limited access — no employee data, Finance, Legal, or HR',
  },
  {
    id: 'support_agent',
    label: 'Support Agent',
    icon: '🎫',
    description: 'Tickets and customers only — no employee data',
  },
]

export default function SessionSetup() {
  const { startSession } = useRole()
  const { theme, toggleTheme } = useTheme()
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [selectedRole, setSelectedRole] = useState('')

  const canStart = name.trim() !== '' && selectedRole !== ''

  function handleStart() {
    if (!canStart) return
    startSession(name.trim(), selectedRole)
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && canStart) {
      handleStart()
    }
  }

  return (
    <div className="session-overlay">
      <div className="session-card">
        <button
          className="session-theme-toggle"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
        >
          {theme === 'dark' ? '☀' : '☾'}
        </button>

        <div className="session-header">
          <span className="session-logo">⬡</span>
          <h1 className="session-title">TechCorp Enterprise AI Platform</h1>
          <p className="session-subtitle">Start a session to access the platform</p>
        </div>

        <div className="session-fields">
          <label className="session-label" htmlFor="session-name">Your Name</label>
          <input
            id="session-name"
            className="session-input"
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. Ilkin Hamzayev"
            autoFocus
          />

          <label className="session-label" htmlFor="session-password">Password</label>
          <input
            id="session-password"
            className="session-input"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="••••••••"
          />
        </div>

        <div className="session-roles">
          <p className="session-label">Select Role</p>
          <div className="session-role-cards">
            {ROLES.map(role => (
              <button
                key={role.id}
                className={`session-role-card ${selectedRole === role.id ? 'selected' : ''}`}
                onClick={() => setSelectedRole(role.id)}
                type="button"
              >
                <span className="session-role-icon">{role.icon}</span>
                <span className="session-role-label">{role.label}</span>
                <span className="session-role-desc">{role.description}</span>
              </button>
            ))}
          </div>
        </div>

        <button
          className="session-start-button"
          onClick={handleStart}
          disabled={!canStart}
        >
          Start Session
        </button>
      </div>
    </div>
  )
}
