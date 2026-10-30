import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const form = new FormData()
      form.append('username', email)
      form.append('password', password)
      const res = await api.post('/auth/login', form)
      localStorage.setItem('token', res.data.access_token)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-page-bg">
      <div className="w-full max-w-md bg-card-bg border border-card-border rounded-card shadow-sm p-8">
        <div className="mb-6 text-center">
          <div className="font-serif text-xl text-heading">AICTE / Complaint Monitoring</div>
          <div className="text-sm text-muted mt-1">Sign in to access the dashboard</div>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label htmlFor="login-email" className="block text-sm mb-1 text-heading">Email</label>
            <input id="login-email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} aria-invalid={!!error} className="w-full border border-card-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-success/30" required />
          </div>
          <div>
            <label htmlFor="login-password" className="block text-sm mb-1 text-heading">Password</label>
            <input id="login-password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={!!error} className="w-full border border-card-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-success/30" required />
          </div>
          {error && <div role="alert" className="text-sm text-red-600">{error}</div>}
          <button disabled={loading} className="w-full bg-primary text-white rounded-lg py-2 text-sm hover:opacity-95 disabled:opacity-60">{loading ? 'Signing in...' : 'Sign In'}</button>
        </form>
        <div className="mt-6 text-xs text-muted">
          <div className="font-medium mb-1">Demo users (dev only)</div>
          <div>admin@aicte.gov.in / admin123 · mgmt@aicte.gov.in / mgmt123</div>
          <div>rb.officer@aicte.gov.in / rb123 · pgrc.officer@aicte.gov.in / pgrc123</div>
          <div>ro.chennai@aicte.gov.in / ro123</div>
        </div>
      </div>
    </div>
  )
}
