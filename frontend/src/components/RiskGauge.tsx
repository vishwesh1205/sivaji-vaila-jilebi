export default function RiskGauge({ score, size = 96 }: { score: number; size?: number }) {
  const radius = 38
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (Math.min(100, Math.max(0, score)) / 100) * circumference
  const color = score >= 70 ? '#B42318' : score >= 40 ? '#B54708' : '#1E8E73'
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="#E7ECF1" strokeWidth="8" fill="none" />
        <circle cx={size / 2} cy={size / 2} r={radius} stroke={color} strokeWidth="8" fill="none" strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" />
      </svg>
      <div className="absolute text-center">
        <div className="text-lg font-semibold text-heading">{Math.round(score)}</div>
        <div className="text-[10px] text-muted">/ 100</div>
      </div>
    </div>
  )
}
