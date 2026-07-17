import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ThemeProvider } from './context/ThemeContext'
import { RoleProvider } from './context/RoleContext'
import App from './App'
import './index.css'

// Set theme attribute before React hydrates to prevent flash of unstyled content
const savedTheme = localStorage.getItem('techcorp-theme') || 'dark'
document.documentElement.setAttribute('data-theme', savedTheme)

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider>
      <RoleProvider>
        <App />
      </RoleProvider>
    </ThemeProvider>
  </StrictMode>,
)