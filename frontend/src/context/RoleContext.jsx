import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const RoleContext = createContext(null)

function getInitialRole() {
  const stored = localStorage.getItem('techcorp-role')
  if (stored === 'engineering_admin' || stored === 'sales_intern' || stored === 'support_agent') {
    return stored
  }
  return 'engineering_admin'
}

function getInitialName() {
  return localStorage.getItem('techcorp-user') || ''
}

export function RoleProvider({ children }) {
  const [activeRole, setActiveRole] = useState(getInitialRole)
  const [userName, setUserName] = useState(getInitialName)

  useEffect(() => {
    localStorage.setItem('techcorp-role', activeRole)
  }, [activeRole])

  useEffect(() => {
    localStorage.setItem('techcorp-user', userName)
  }, [userName])

  const isSessionActive = userName !== ''

  const startSession = useCallback((name, role) => {
    setUserName(name)
    setActiveRole(role)
  }, [])

  const logout = useCallback(() => {
    setUserName('')
    setActiveRole('engineering_admin')
    localStorage.removeItem('techcorp-user')
    localStorage.removeItem('techcorp-role')
  }, [])

  return (
    <RoleContext.Provider value={{
      activeRole,
      setActiveRole,
      userName,
      isSessionActive,
      startSession,
      logout,
    }}>
      {children}
    </RoleContext.Provider>
  )
}

export function useRole() {
  const ctx = useContext(RoleContext)
  if (!ctx) throw new Error('useRole must be used within RoleProvider')
  return ctx
}
