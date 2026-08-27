import type { ReactNode } from 'react'
import { Loader2 } from 'lucide-react'

export function LoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-slate-400">
      <Loader2 className="h-8 w-8 animate-spin text-cyber-accent" />
      <p className="text-sm">{message}</p>
    </div>
  )
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-6 text-center">
      <p className="text-sm text-red-400">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-md bg-red-500/20 px-4 py-1.5 text-xs text-red-300 hover:bg-red-500/30"
        >
          Retry
        </button>
      )}
    </div>
  )
}

export function MetricCard({
  label,
  value,
  icon,
  accent = 'cyan',
}: {
  label: string
  value: string | number
  icon: ReactNode
  accent?: 'cyan' | 'green' | 'amber' | 'red' | 'slate'
}) {
  const colors = {
    cyan: 'text-cyber-accent ring-cyan-500/20 bg-cyan-500/5',
    green: 'text-cyber-success ring-emerald-500/20 bg-emerald-500/5',
    amber: 'text-cyber-warning ring-amber-500/20 bg-amber-500/5',
    red: 'text-cyber-danger ring-red-500/20 bg-red-500/5',
    slate: 'text-slate-300 ring-slate-500/20 bg-slate-500/5',
  }

  return (
    <div
      className={`rounded-xl border border-cyber-border p-4 ring-1 ${colors[accent]}`}
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider text-slate-500">
          {label}
        </span>
        <span className="opacity-70">{icon}</span>
      </div>
      <p className="text-2xl font-semibold text-white">{value}</p>
    </div>
  )
}
