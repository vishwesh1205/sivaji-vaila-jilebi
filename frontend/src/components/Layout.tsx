import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Bell, LayoutDashboard, Building2, FileText, AlertTriangle, CheckSquare, BarChart3, Upload, Search, Database, TrendingUp, Calculator } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/institutions', label: 'Institutions', icon: Building2 },
  { to: '/cases', label: 'Case Tracking', icon: FileText },
  { to: '/overlaps', label: 'Overlap Alerts', icon: AlertTriangle },
  { to: '/emerging', label: 'Emerging Issues', icon: TrendingUp },
  { to: '/impact', label: 'Impact Simulator', icon: Calculator },
  { to: '/sources', label: 'Data Sources', icon: Database },
  { to: '/review', label: 'Resolution Review', icon: CheckSquare },
  { to: '/reports', label: 'Reports & Analytics', icon: BarChart3 },
  { to: '/import', label: 'Data Import', icon: Upload },
]

export default function Layout() {
  const navigate = useNavigate()
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: async () => (await api.get('/auth/me')).data })
  const { data: notifs } = useQuery({ queryKey: ['notifs'], queryFn: async () => (await api.get('/notifications')).data, refetchInterval: 30000 })
  const unread = notifs?.filter((n: any) => !n.is_read).length || 0

  return (
    <div className="min-h-screen flex">
      <aside className="w-[232px] bg-sidebar-bg text-sidebar-text flex flex-col">
        <div className="px-6 py-5 border-b border-white/10">
          <div className="font-serif text-lg text-white">AICTE / Complaint Monitoring</div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${isActive ? 'bg-sidebar-active text-white' : 'hover:bg-white/5'}`
              }
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
          <div className="pt-4 mt-4 border-t border-white/10">
            <div className="px-3 text-xs uppercase tracking-wide text-white/50 mb-2">Bureaus</div>
            <div className="px-3 text-sm">RB · PGRC · Regional Offices</div>
          </div>
        </nav>
      </aside>
      <div className="flex-1 flex flex-col">
        <header className="h-16 bg-white border-b border-card-border flex items-center px-6 gap-4">
          <div className="flex-1 flex items-center gap-2 max-w-xl">
            <Search size={18} className="text-muted" />
            <input
              placeholder="Search institution / AICTE ID / Case ID"
              className="flex-1 bg-transparent text-sm focus:outline-none"
              aria-label="Global search"
            />
          </div>
          <button onClick={() => navigate('/notifications')} className="relative p-2 rounded-lg hover:bg-page-bg" aria-label="Notifications">
            <Bell size={18} />
            {unread > 0 && <span className="absolute -top-1 -right-1 w-2 h-2 bg-alert-badge rounded-full"></span>}
          </button>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-sm font-medium text-heading">{me?.name}</div>
              <div className="text-xs text-muted">{me?.role}</div>
            </div>
            <div className="w-9 h-9 rounded-full bg-sidebar-bg text-white flex items-center justify-center text-sm">
              {me?.name?.[0]}
            </div>
            <button onClick={() => { localStorage.removeItem('token'); navigate('/login'); }} className="text-sm text-muted hover:text-heading">Logout</button>
          </div>
        </header>
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
