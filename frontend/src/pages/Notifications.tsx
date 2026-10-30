import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'

const LABELS: Record<string, string> = {
  OVERLAP: 'Overlap coordination',
  ESCALATION: 'Management escalation',
  SLA: 'SLA notice',
  PENDING_REMINDER: 'Pending-action reminder',
}

function messageFor(n: any) {
  if (n.payload?.message) return n.payload.message
  if (n.type === 'SLA') return `Case ${n.payload?.case_id || ''} is ${n.payload?.days_open ?? '?'} days old (${n.payload?.bucket || 'SLA'}).`
  if (n.type === 'PENDING_REMINDER') return `Case ${n.payload?.case_id || ''} has had no action for ${n.payload?.days_since_action ?? '?'} days.`
  if (n.payload?.alert_id) return `Overlap alert #${n.payload.alert_id} requires attention.`
  return JSON.stringify(n.payload)
}

export default function Notifications() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['notifs'], queryFn: async () => (await api.get('/notifications')).data })
  const markRead = useMutation({
    mutationFn: async (id: number) => (await api.post(`/notifications/${id}/read`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifs'] }),
  })
  const markAll = useMutation({
    mutationFn: async (ids: number[]) => Promise.all(ids.map((id) => api.post(`/notifications/${id}/read`))),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifs'] }),
  })
  const unread = (data || []).filter((n: any) => !n.is_read)
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-heading">Notifications</h1>
          <p className="text-sm text-muted">Alerts and reminders · {unread.length} unread</p>
        </div>
        {unread.length > 0 && <button onClick={() => markAll.mutate(unread.map((n: any) => n.id))} disabled={markAll.isPending} className="px-3 py-1.5 rounded-lg text-sm border border-card-border disabled:opacity-50">{markAll.isPending ? 'Marking…' : 'Mark all as read'}</button>}
      </div>
      <div className="bg-card-bg border border-card-border rounded-card divide-y divide-card-border">
        {data?.map((n: any) => (
          <div key={n.id} className={`p-4 flex items-start justify-between gap-4 ${n.is_read ? 'opacity-60' : ''}`}>
            <div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${n.type === 'ESCALATION' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-page-bg text-muted border-card-border'}`}>{LABELS[n.type] || n.type}</span>
                {!n.is_read && <span className="w-2 h-2 bg-success rounded-full"></span>}
              </div>
              <div className="text-sm text-heading mt-1">{messageFor(n)}</div>
              <div className="text-xs text-muted mt-1">{n.created_at?.replace('T', ' ').slice(0, 16)}</div>
            </div>
            {!n.is_read && <button onClick={() => markRead.mutate(n.id)} disabled={markRead.isPending} className="px-3 py-1.5 rounded-lg text-xs border border-card-border hover:bg-page-bg disabled:opacity-50">Mark read</button>}
          </div>
        ))}
        {!data?.length && <div className="p-6 text-sm text-muted">No notifications.</div>}
      </div>
    </div>
  )
}
