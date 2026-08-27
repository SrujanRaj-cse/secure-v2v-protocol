import type { ReactNode } from 'react'
import { ShieldAlert } from 'lucide-react'

export function AttackCard({
  title,
  description,
  onLaunch,
  loading,
  children,
  variant = 'default',
}: {
  title: string
  description: string
  onLaunch: () => void
  loading?: boolean
  children?: ReactNode
  variant?: 'default' | 'replay' | 'tamper' | 'impersonation'
}) {
  const borderColors = {
    default: 'border-cyber-border',
    replay: 'border-amber-500/30',
    tamper: 'border-red-500/30',
    impersonation: 'border-purple-500/30',
  }

  return (
    <div
      className={`rounded-xl border bg-cyber-panel p-5 ${borderColors[variant]}`}
    >
      <div className="mb-3 flex items-center gap-2">
        <ShieldAlert className="h-5 w-5 text-cyber-warning" />
        <h3 className="font-semibold text-white">{title}</h3>
      </div>
      <p className="mb-4 text-sm text-slate-400">{description}</p>
      <button
        type="button"
        onClick={onLaunch}
        disabled={loading}
        className="w-full rounded-lg bg-red-500/10 px-4 py-2.5 text-sm font-medium uppercase tracking-wider text-red-400 ring-1 ring-red-500/30 transition hover:bg-red-500/20 disabled:opacity-50"
      >
        {loading ? 'Launching...' : `Launch ${title}`}
      </button>
      {children}
    </div>
  )
}

export function Alert({
  accepted,
  reason,
  mechanism,
}: {
  accepted: boolean
  reason: string
  mechanism?: string
}) {
  return (
    <div
      className={`mt-4 rounded-lg border p-4 ${
        accepted
          ? 'border-emerald-500/30 bg-emerald-500/5'
          : 'border-red-500/30 bg-red-500/5'
      }`}
    >
      <p
        className={`text-sm font-semibold ${accepted ? 'text-emerald-400' : 'text-red-400'}`}
      >
        {accepted ? '✓ MESSAGE ACCEPTED' : '🚨 MESSAGE REJECTED'}
      </p>
      <p className="mt-1 text-sm text-slate-300">
        <span className="text-slate-500">Reason: </span>
        {reason}
      </p>
      {mechanism && (
        <p className="mt-1 text-xs text-slate-500">
          Security mechanism: {mechanism}
        </p>
      )}
    </div>
  )
}
