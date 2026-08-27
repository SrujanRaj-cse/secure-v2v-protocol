import type { SecurityEvent } from '../types'
import { Trash2 } from 'lucide-react'

const severityStyles = {
  info: 'border-l-slate-500 bg-slate-800/30',
  success: 'border-l-emerald-500 bg-emerald-500/5',
  warning: 'border-l-amber-500 bg-amber-500/5',
  error: 'border-l-red-500 bg-red-500/5',
}

const severityBadge = {
  info: 'bg-slate-700 text-slate-300',
  success: 'bg-emerald-500/20 text-emerald-400',
  warning: 'bg-amber-500/20 text-amber-400',
  error: 'bg-red-500/20 text-red-400',
}

export function EventLogPanel({
  events,
  onClear,
  filters,
  onFilterChange,
}: {
  events: SecurityEvent[]
  onClear: () => void
  filters: { severity: string; vehicle_id: string; search: string }
  onFilterChange: (key: string, value: string) => void
}) {
  return (
    <div className="rounded-xl border border-cyber-border bg-cyber-panel">
      <div className="flex flex-wrap items-center gap-3 border-b border-cyber-border p-4">
        <select
          value={filters.severity}
          onChange={(e) => onFilterChange('severity', e.target.value)}
          className="rounded-md border border-cyber-border bg-cyber-bg px-3 py-1.5 text-sm text-slate-300"
        >
          <option value="all">All severities</option>
          <option value="info">Info</option>
          <option value="success">Success</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
        </select>
        <select
          value={filters.vehicle_id}
          onChange={(e) => onFilterChange('vehicle_id', e.target.value)}
          className="rounded-md border border-cyber-border bg-cyber-bg px-3 py-1.5 text-sm text-slate-300"
        >
          <option value="all">All vehicles</option>
          <option value="A001">A001</option>
          <option value="B001">B001</option>
          <option value="C001">C001</option>
        </select>
        <input
          type="search"
          placeholder="Search logs..."
          value={filters.search}
          onChange={(e) => onFilterChange('search', e.target.value)}
          className="flex-1 rounded-md border border-cyber-border bg-cyber-bg px-3 py-1.5 text-sm text-slate-300 placeholder:text-slate-600"
        />
        <button
          type="button"
          onClick={onClear}
          className="flex items-center gap-1.5 rounded-md border border-cyber-border px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-800"
        >
          <Trash2 className="h-3.5 w-3.5" />
          Clear
        </button>
      </div>
      <div className="max-h-[500px] overflow-y-auto p-2">
        {events.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            No events yet — send a message or launch an attack
          </p>
        ) : (
          events.map((e) => (
            <div
              key={e.id}
              className={`mb-1 border-l-2 px-3 py-2 ${severityStyles[e.severity]}`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`rounded px-1.5 py-0.5 text-[10px] uppercase ${severityBadge[e.severity]}`}
                >
                  {e.severity}
                </span>
                <span className="font-mono text-[10px] text-slate-600">
                  {new Date(e.timestamp).toLocaleTimeString()}
                </span>
                {e.vehicle_id && (
                  <span className="font-mono text-[10px] text-cyan-500/70">
                    {e.vehicle_id}
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-sm text-slate-300">{e.message}</p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
