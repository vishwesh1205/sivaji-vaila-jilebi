import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'

const Login = lazy(() => import('./pages/Login'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Institutions = lazy(() => import('./pages/Institutions'))
const Institution360 = lazy(() => import('./pages/Institution360'))
const CaseTracking = lazy(() => import('./pages/CaseTracking'))
const CaseDetail = lazy(() => import('./pages/CaseDetail'))
const OverlapAlerts = lazy(() => import('./pages/OverlapAlerts'))
const ResolutionReview = lazy(() => import('./pages/ResolutionReview'))
const MatchingEvaluation = lazy(() => import('./pages/MatchingEvaluation'))
const Reports = lazy(() => import('./pages/Reports'))
const Import = lazy(() => import('./pages/Import'))
const Notifications = lazy(() => import('./pages/Notifications'))
const DataSources = lazy(() => import('./pages/DataSources'))
const EmergingIssues = lazy(() => import('./pages/EmergingIssues'))
const ImpactSimulator = lazy(() => import('./pages/ImpactSimulator'))

function PrivateRoute({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem('token')
  return token ? children : <Navigate to="/login" replace />
}

function PageFallback() {
  return <div className="p-6 text-sm text-muted">Loading…</div>
}

export default function App() {
  return (
    <Suspense fallback={<PageFallback />}>
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
          <Route path="matching" element={<MatchingEvaluation />} />
          <Route path="reports" element={<Reports />} />
          <Route path="import" element={<Import />} />
          <Route path="notifications" element={<Notifications />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
