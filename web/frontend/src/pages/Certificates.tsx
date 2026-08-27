import { useEffect, useState } from 'react'
import { Building2 } from 'lucide-react'
import { api } from '../services/api'
import type { CertificateInfo, CertificatesResponse } from '../types'
import { CertificateCard } from '../components/CertificateCard'
import { Modal } from '../components/Modal'
import { LoadingState, ErrorState } from '../components/MetricCard'

export function CertificatesPage() {
  const [data, setData] = useState<CertificatesResponse | null>(null)
  const [detail, setDetail] = useState<CertificateInfo | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getCertificates()
      .then(setData)
      .catch((e) => setError(e.message))
  }, [])

  const viewDetail = async (id: string) => {
    try {
      const d = await api.getCertificateDetail(id)
      setDetail(d)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load detail')
    }
  }

  if (error && !data) return <ErrorState message={error} />
  if (!data) return <LoadingState />

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white">
          Certificate Authority
        </h2>
        <p className="text-sm text-slate-500">
          X.509 PKI — vehicle identity and public key management
        </p>
      </div>

      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-5">
        <div className="flex items-center gap-3">
          <Building2 className="h-6 w-6 text-cyber-accent" />
          <div>
            <h3 className="font-semibold text-white">{data.ca.name}</h3>
            <p className="text-sm text-slate-400">
              Status: {data.ca.status} · Algorithm: {data.ca.algorithm} ·{' '}
              {data.ca.certificate_count} certificates issued
            </p>
          </div>
        </div>
        <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
          <Detail label="Issuer" value={data.ca.issuer} />
          <Detail
            label="Valid From"
            value={new Date(data.ca.not_valid_before).toLocaleString()}
          />
          <Detail
            label="Valid Until"
            value={new Date(data.ca.not_valid_after).toLocaleString()}
          />
          <Detail label="CA Public Key" value={data.ca.public_key_abbrev} mono />
        </dl>
      </div>

      <div>
        <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-slate-500">
          Issued Vehicle Certificates
        </h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.vehicles.map((c) => (
            <CertificateCard
              key={c.vehicle_id}
              cert={c}
              onView={() => viewDetail(c.vehicle_id)}
            />
          ))}
        </div>
      </div>

      <Modal
        open={!!detail}
        onClose={() => setDetail(null)}
        title={`Certificate — ${detail?.vehicle_id}`}
      >
        {detail && (
          <dl className="space-y-3 text-sm">
            <Detail label="Subject" value={detail.subject} />
            <Detail label="Issuer" value={detail.issuer} />
            <Detail label="Serial" value={detail.serial_number} mono />
            <Detail label="Algorithm" value={detail.algorithm} />
            <Detail label="Public Key" value={detail.public_key_abbrev} mono />
            <Detail
              label="Valid From"
              value={new Date(detail.not_valid_before).toLocaleString()}
            />
            <Detail
              label="Valid Until"
              value={new Date(detail.not_valid_after).toLocaleString()}
            />
            {detail.verification && (
              <Detail
                label="Verification"
                value={
                  detail.verification.valid
                    ? 'VALID — CA signed and registered'
                    : detail.verification.reason
                }
              />
            )}
          </dl>
        )}
      </Modal>
    </div>
  )
}

function Detail({
  label,
  value,
  mono,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className={`text-slate-300 ${mono ? 'break-all font-mono text-xs' : ''}`}>
        {value}
      </dd>
    </div>
  )
}
