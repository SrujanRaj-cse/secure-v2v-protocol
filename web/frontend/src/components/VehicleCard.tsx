import type { Vehicle } from '../types'
import { CheckCircle2, XCircle } from 'lucide-react'

export function VehicleCard({ vehicle }: { vehicle: Vehicle }) {
  const certOk = vehicle.certificate_status === 'VALID'
  const secure = vehicle.security_status === 'SECURE'

  return (
    <div className="rounded-xl border border-cyber-border bg-cyber-panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-mono text-lg font-semibold text-white">
          {vehicle.vehicle_id}
        </h3>
        <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
          {vehicle.direction}
        </span>
      </div>
      <div className="space-y-2 text-sm">
        <StatusRow
          ok={certOk}
          label={certOk ? 'Certificate Valid' : 'Certificate Invalid'}
        />
        <StatusRow ok={secure} label={secure ? 'Secure' : 'Compromised'} />
        <p className="text-slate-500">
          Sequence:{' '}
          <span className="font-mono text-slate-300">
            {vehicle.sequence_number}
          </span>
        </p>
        <p className="text-slate-500">
          Speed:{' '}
          <span className="text-slate-300">{vehicle.speed} km/h</span>
        </p>
        {vehicle.last_event && (
          <p className="truncate text-xs text-slate-500">
            Last: {vehicle.last_event}
          </p>
        )}
      </div>
    </div>
  )
}

function StatusRow({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2">
      {ok ? (
        <CheckCircle2 className="h-4 w-4 text-cyber-success" />
      ) : (
        <XCircle className="h-4 w-4 text-cyber-danger" />
      )}
      <span className={ok ? 'text-emerald-400' : 'text-red-400'}>{label}</span>
    </div>
  )
}
