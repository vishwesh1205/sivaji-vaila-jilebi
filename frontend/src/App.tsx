import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Institutions from './pages/Institutions'
import Institution360 from './pages/Institution360'
import CaseTracking from './pages/CaseTracking'
import CaseDetail from './pages/CaseDetail'
import OverlapAlerts from './pages/OverlapAlerts'
import ResolutionReview from './pages/ResolutionReview'
import Reports from './pages/Reports'
import Import from './pages/Import'
import Notifications from './pages/Notifications'
import DataSources from './pages/DataSources'
import EmergingIssues from './pages/EmergingIssues'
import ImpactSimulator from './pages/ImpactSimulator'

function PrivateRoute({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem('token')
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="institutions" element={<Institutions />} />
        <Route path="institutions/:id" element={<Institution360 />} />
        <Route path="cases" element={<CaseTracking />} />
        <Route path="cases/:id" element={<CaseDetail />} />
        <Route path="overlaps" element={<OverlapAlerts />} />
        <Route path="emerging" element={<EmergingIssues />} />
        <Route path="impact" element={<ImpactSimulator />} />
        <Route path="sources" element={<DataSources />} />
        <Route path="review" element={<ResolutionReview />} />
        <Route path="reports" element={<Reports />} />
        <Route path="import" element={<Import />} />
        <Route path="notifications" element={<Notifications />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
