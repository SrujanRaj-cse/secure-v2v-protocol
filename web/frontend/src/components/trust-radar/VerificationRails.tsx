import type { RadarAttackOverlay, RadarRecipient } from '../../types/trustRadar'
import type { VerificationGate } from '../../types'
import { gatesFromPipeline } from '../../services/trustRadarData.mjs'

const gateColor: Record<VerificationGate['status'], string> = {
  passed: 'bg-[#3ddc97] border-[#3ddc97] text-[#3ddc97]',
  failed: 'bg-[#ff5c5c] border-[#ff5c5c] text-[#ff5c5c]',
  skipped: 'bg-transparent border-[#3a4752] text-[#6b7f90]',
  not_reported: 'bg-transparent border-[#3a4752] text-[#6b7f90]',
  warning: 'bg-[#f5b942] border-[#f5b942] text-[#f5b942]',
  relevant: 'bg-transparent border-[#f5b942] text-[#f5b942]',
  not_relevant: 'bg-transparent border-[#3a4752] text-[#6b7f90]',
}

function statusText(recipient: RadarRecipient | undefined, attack: RadarAttackOverlay | null, vehicleId: string) {
  if (attack?.receiverId === vehicleId) {
    const failed = attack.pipeline.find((step) => step.status === 'failed')
    return failed ? `stopped at ${failed.name.toLowerCase()}: ${failed.detail || attack.reason}` : attack.accepted ? 'attack packet accepted' : attack.reason
  }
  if (!recipient) return 'awaiting recorded result'
  if (recipient.delivery_status === 'outside_range') return recipient.rejection_reason || 'outside range'
  if (recipient.delivery_status === 'dropped') return 'dropped by channel'
  if (recipient.delivery_status === 'offline') return 'vehicle offline'
  if (!recipient.accepted) return `${recipient.verification_status}: ${recipient.rejection_reason || 'rejected'}`
  if (recipient.safety?.warning) return 'warning raised'
  if (recipient.safety?.relevant) return 'authentic, relevant; no warning threshold reached'
  if (recipient.safety) return 'authentic, not relevant'
  return 'authentic; relevance not reported'
}

export function VerificationRails({
  recipientVehicles,
  recipients,
  attack,
  phase,
}: {
  recipientVehicles: Array<{ vehicle_id: string }>
  recipients: RadarRecipient[]
  attack: RadarAttackOverlay | null
  phase: number
}) {
  const byId = new Map(recipients.map((item) => [item.receiver_id, item]))
  return <section className="rounded-xl border border-[#1f2d3a] bg-[#0e161e] p-4" aria-label="Recipient verification rails">
    <div className="mb-4 flex items-center justify-between gap-2">
      <div><h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-[#d5e0ea]">Verification rails</h2><p className="mt-1 text-[10px] text-[#6b7f90]">Actual backend status · hollow means not reported or not reached</p></div>
      <div className="hidden gap-2 text-[9px] uppercase text-[#6b7f90] md:flex">{['Schema', 'Certificate', 'Signature', 'Freshness', 'Replay', 'Relevance'].map((gate) => <span key={gate} className="w-8 text-center">{gate.slice(0, 3)}</span>)}</div>
    </div>
    {recipientVehicles.length === 0 ? <p className="py-8 text-center text-xs text-[#6b7f90]">No other registered vehicles are available.</p> : <div className="space-y-2">
      {recipientVehicles.map(({ vehicle_id: id }) => {
        const recipient = byId.get(id)
        const attackApplies = attack?.receiverId === id
        const attackSafety = attack?.safety
        const attackRelevance = attackSafety ? attackSafety.warning ? 'warning' : attackSafety.relevant ? 'relevant' : 'not_relevant' : 'not_reported'
        const currentGates: VerificationGate[] = attackApplies
          ? gatesFromPipeline(attack.pipeline, attackRelevance, attackSafety?.reason ?? 'Not reported by this attack endpoint.')
          : recipient?.verification_gates ?? []
        return <div key={id} className="grid grid-cols-[62px_1fr] items-center gap-2 rounded-lg border border-[#1f2d3a] bg-[#0b1016] px-3 py-3 md:grid-cols-[72px_1fr_240px]">
          <span className="font-mono text-xs font-semibold text-[#d5e0ea]">{id}</span>
          <div className="flex items-center gap-2" aria-label={`${id} verification gates`}>
            {['Schema', 'Certificate', 'Signature', 'Freshness', 'Replay', 'Relevance'].map((name, index) => {
              const gate = currentGates.find((item) => item.name === name)
              const revealed = phase >= (index === 5 ? 3 : 2)
              const status = revealed ? gate?.status ?? 'not_reported' : 'not_reported'
              return <span
                key={name}
                tabIndex={0}
                title={`${name}: ${gate?.reason || 'Not reported by backend.'}`}
                aria-label={`${name}: ${status}. ${gate?.reason || 'Not reported by backend.'}`}
                className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border text-[8px] outline-none transition-colors focus-visible:ring-2 focus-visible:ring-white ${gateColor[status]} ${revealed ? 'opacity-100' : 'opacity-50'}`}
                style={{ transitionDelay: `${index * 90}ms` }}
              >{status === 'failed' ? '×' : status === 'warning' ? '!' : status === 'passed' ? '✓' : ''}</span>
            })}
          </div>
          <p className="col-span-2 break-words text-[11px] leading-4 text-[#8fa2b2] md:col-span-1">{statusText(recipient, attack, id)}</p>
        </div>
      })}
    </div>}
  </section>
}
