const styles: Record<string, string> = {
  LIVE_PUBLIC: 'bg-blue-50 text-blue-700 border-blue-200',
  SIMULATOR: 'bg-amber-50 text-amber-800 border-amber-200',
  FILE_UPLOAD: 'bg-violet-50 text-violet-700 border-violet-200',
  MANUAL: 'bg-slate-100 text-slate-700 border-slate-200',
}

const labels: Record<string, string> = {
  LIVE_PUBLIC: 'LIVE PUBLIC',
  SIMULATOR: 'SIMULATOR',
  FILE_UPLOAD: 'FILE UPLOAD',
  MANUAL: 'MANUAL',
}

export default function SourceBadge({ type, name, compact = false }: { type?: string | null; name?: string | null; compact?: boolean }) {
  const sourceType = type || 'MANUAL'
  const sim = sourceType === 'SIMULATOR'
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border ${styles[sourceType] || styles.MANUAL}`}
      title={sim ? 'SIMULATOR – synthetic data, not live public data' : sourceType === 'LIVE_PUBLIC' ? 'Live public source' : sourceType === 'FILE_UPLOAD' ? 'Uploaded file source' : 'Manually entered record'}
    >
      {labels[sourceType] || sourceType}
      {!compact && name ? <span className="opacity-70">· {name}</span> : null}
    </span>
  )
}
