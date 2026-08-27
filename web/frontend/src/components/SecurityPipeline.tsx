import type { PipelineStep } from '../types'
import {
  AlertTriangle,
  ArrowDown,
  CheckCircle2,
  Circle,
  Loader2,
  MinusCircle,
  XCircle,
} from 'lucide-react'

const statusIcon = {
  pending: Circle,
  processing: Loader2,
  success: CheckCircle2,
  failed: XCircle,
  warning: AlertTriangle,
  skipped: MinusCircle,
}

const statusColor = {
  pending: 'text-slate-500',
  processing: 'text-cyan-400 animate-spin',
  success: 'text-emerald-400',
  failed: 'text-red-400',
  warning: 'text-amber-400',
  skipped: 'text-slate-600',
}

export function SecurityPipeline({ steps }: { steps: PipelineStep[] }) {
  return (
    <div className="rounded-xl border border-cyber-border bg-cyber-panel p-5">
      <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-slate-500">
        Security Pipeline
      </h3>
      <div className="space-y-1">
        {steps.map((step, i) => {
          const Icon = statusIcon[step.status] || Circle
          const color = statusColor[step.status] || 'text-slate-500'
          return (
            <div key={`${step.name}-${i}`}>
              <div className="flex items-start gap-3 rounded-lg px-2 py-2 hover:bg-slate-800/30">
                <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${color}`} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-200">
                    {step.name}
                  </p>
                  {step.detail && (
                    <p className="truncate font-mono text-xs text-slate-500">
                      {step.detail}
                    </p>
                  )}
                </div>
                <span
                  className={`shrink-0 text-[10px] uppercase tracking-wider ${color}`}
                >
                  {step.status}
                </span>
              </div>
              {i < steps.length - 1 && (
                <div className="ml-5 flex justify-center py-0.5">
                  <ArrowDown className="h-3 w-3 text-slate-700" />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
