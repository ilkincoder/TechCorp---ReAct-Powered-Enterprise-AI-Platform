import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryProvider } from './context/QueryContext'
import { useRole } from './context/RoleContext'
import SessionSetup from './components/SessionSetup'
import DashboardLayout from './features/dashboard/DashboardLayout'
import DashboardPage from './features/dashboard/DashboardPage'
import ChatPageWrapper from './features/dashboard/ChatPageWrapper'
import IncidentsPage from './features/dashboard/pages/IncidentsPage'
import TicketsPage from './features/dashboard/pages/TicketsPage'
import ProjectsPage from './features/dashboard/pages/ProjectsPage'
import SubscriptionsPage from './features/dashboard/pages/SubscriptionsPage'
import TeamPage from './features/dashboard/pages/TeamPage'
import Reports from './pages/Reports'
import './App.css'

function AppRoutes() {
  return (
    <QueryProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<DashboardLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/chat" element={<ChatPageWrapper />} />
            <Route path="/incidents" element={<IncidentsPage />} />
            <Route path="/tickets" element={<TicketsPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/subscriptions" element={<SubscriptionsPage />} />
            <Route path="/team" element={<TeamPage />} />
            <Route path="/reports" element={<Reports />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryProvider>
  )
}

export default function App() {
  const { isSessionActive } = useRole()

  if (!isSessionActive) {
    return <SessionSetup />
  }

  return <AppRoutes />
}
