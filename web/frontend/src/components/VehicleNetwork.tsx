import type { Vehicle } from '../types'
import { ArrowDown, Shield } from 'lucide-react'

export function VehicleNetwork({ vehicles }: { vehicles: Vehicle[] }) {
  const sorted = [...vehicles].sort((a, b) =>
    a.vehicle_id.localeCompare(b.vehicle_id),
  )

  return (
    <div className="rounded-xl border border-cyber-border bg-cyber-panel p-6">
      <h2 className="mb-6 text-sm font-medium uppercase tracking-wider text-slate-500">
        Vehicle Network
      </h2>
      <div className="flex flex-col items-center gap-2">
        {sorted.map((v, i) => (
          <div key={v.vehicle_id} className="flex flex-col items-center">
            <div
              className={`flex w-48 flex-col items-center rounded-lg border px-4 py-3 ${
                v.security_status === 'SECURE'
                  ? 'border-emerald-500/30 bg-emerald-500/5'
                  : 'border-red-500/30 bg-red-500/5'
              }`}
            >
              <span className="font-mono text-lg font-bold text-white">
                {v.vehicle_id}
              </span>
              <span className="mt-1 flex items-center gap-1 text-xs text-slate-400">
                <Shield className="h-3 w-3" />
                {v.certificate_status}
              </span>
              <span className="text-xs text-slate-500">
                Seq: {v.sequence_number}
              </span>
            </div>
            {i < sorted.length - 1 && (
              <div className="my-1 flex flex-col items-center text-cyan-500/60">
                <div className="h-4 w-px bg-cyan-500/40" />
                <span className="my-0.5 flex items-center gap-1 text-[10px] uppercase tracking-widest">
                  Secure V2V
                </span>
                <ArrowDown className="h-3 w-3" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
