import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'

export default function Notifications() {
  const { data } = useQuery({ queryKey: ['notifs'], queryFn: async () => (await api.get('/notifications')).data })
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-heading">Notifications</h1>
        <p className="text-sm text-muted">Alerts and reminders</p>
      </div>
      <div className="bg-card-bg border border-card-border rounded-card divide-y divide-card-border">
        {data?.map((n: any) => (
          <div key={n.id} className="p-4 flex items-start justify-between">
            <div>
              <div className="text-sm text-heading">{n.type}</div>
              <div className="text-sm text-muted mt-1">{JSON.stringify(n.payload)}</div>
              <div className="text-xs text-muted mt-1">{n.created_at?.replace('T',' ').slice(0,16)}</div>
            </div>
            {!n.is_read && <span className="w-2 h-2 bg-success rounded-full mt-2"></span>}
          </div>
        ))}
      </div>
    </div>
  )
}
