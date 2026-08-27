import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { DashboardPage } from './pages/Dashboard'
import { CommunicationPage } from './pages/Communication'
import { CertificatesPage } from './pages/Certificates'
import { AttacksPage } from './pages/Attacks'
import { EventLogPage } from './pages/EventLogPage'
import { PerformancePage } from './pages/Performance'
import { ArchitecturePage } from './pages/Architecture'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="communication" element={<CommunicationPage />} />
          <Route path="certificates" element={<CertificatesPage />} />
          <Route path="attacks" element={<AttacksPage />} />
          <Route path="events" element={<EventLogPage />} />
          <Route path="performance" element={<PerformancePage />} />
          <Route path="architecture" element={<ArchitecturePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
