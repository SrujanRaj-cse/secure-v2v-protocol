import type { CertificateInfo } from '../types'
import { Award, Eye } from 'lucide-react'

export function CertificateCard({
  cert,
  onView,
}: {
  cert: CertificateInfo
  onView: () => void
}) {
  const valid = cert.status === 'VALID'

  return (
    <div className="rounded-xl border border-cyber-border bg-cyber-panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Award className="h-4 w-4 text-cyber-accent" />
          <span className="font-mono text-lg font-semibold text-white">
            {cert.vehicle_id}
          </span>
        </div>
        <span
          className={`rounded-full px-2 py-0.5 text-xs ${
            valid
              ? 'bg-emerald-500/10 text-emerald-400'
              : 'bg-red-500/10 text-red-400'
          }`}
        >
          {cert.status}
        </span>
      </div>
      <dl className="space-y-1.5 text-xs">
        <Row label="Issuer" value={cert.issuer} />
        <Row label="Algorithm" value={cert.algorithm} />
        <Row label="Public Key" value={cert.public_key_abbrev} mono />
        <Row
          label="Valid Until"
          value={new Date(cert.not_valid_after).toLocaleDateString()}
        />
      </dl>
      <button
        type="button"
        onClick={onView}
        className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-md border border-cyber-border py-1.5 text-xs text-slate-400 hover:bg-slate-800"
      >
        <Eye className="h-3.5 w-3.5" />
        View Details
      </button>
    </div>
  )
}

function Row({
  label,
  value,
  mono,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-slate-500">{label}</dt>
      <dd
        className={`truncate text-right text-slate-300 ${mono ? 'font-mono text-[10px]' : ''}`}
      >
        {value}
      </dd>
    </div>
  )
}
