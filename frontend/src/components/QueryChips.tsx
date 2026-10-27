export default function QueryChips({ chips }: { chips?: string[] }) {
  if (!chips?.length) return null
  return (
    <div className="flex flex-wrap gap-1.5">
      {chips.map((chip, i) => (
        <span key={`${chip}-${i}`} className="px-2 py-0.5 rounded-full text-xs bg-page-bg border border-card-border text-muted">{chip}</span>
      ))}
    </div>
  )
}
