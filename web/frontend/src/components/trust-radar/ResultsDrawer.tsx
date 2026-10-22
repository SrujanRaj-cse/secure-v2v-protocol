import type { RadarRecipient } from '../../types/trustRadar'
import { countRadarRecipients, radarCountsText } from '../../services/trustRadarData.mjs'

export function ResultsDrawer({ recipients }: { recipients: RadarRecipient[] }) {
  const counts = countRadarRecipients(recipients)
  const candidates = recipients.filter((item) => item.delivery_status !== 'sender_excluded')
  return <>
    <p className="sr-only" aria-live="polite">{radarCountsText(counts)}</p>
    <details className="group rounded-xl border border-[#1f2d3a] bg-[#0e161e]">
      <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3 px-4 py-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#4c9be8]">
        <span className="text-xs font-semibold uppercase tracking-[0.15em] text-[#d5e0ea]">Recipient results <span className="ml-2 text-[10px] font-normal normal-case text-[#6b7f90]">open full table</span></span>
        <span className="flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10px] text-[#8fa2b2]">
          <span>{counts.candidates} candidates</span><span>{counts.eligible} eligible</span><span>{counts.delivered} delivered</span><span>{counts.dropped} dropped</span><span>{counts.invalid} invalid</span><span>{counts.verified} verified</span><span className="text-[#f5b942]">{counts.warnings} warnings</span>
        </span>
      </summary>
      <div className="border-t border-[#1f2d3a]">
        {candidates.length === 0 ? <p className="p-4 text-xs text-[#6b7f90]">No recipient outcomes have been recorded.</p> : <div className="overflow-x-auto">
          <table className="w-full min-w-[1000px] text-left text-[10px]">
            <thead className="bg-[#0b1016] uppercase tracking-wider text-[#6b7f90]"><tr>{['Vehicle', 'Distance', 'Eligible', 'Delivery', 'Verification', 'Rejection reason', 'Relevance', 'Warning', 'Latency'].map((heading) => <th key={heading} className="px-3 py-2">{heading}</th>)}</tr></thead>
            <tbody>{candidates.map((item) => {
              const eligible = ['eligible', 'delivered', 'dropped'].includes(item.delivery_status)
              return <tr key={item.receiver_id} className="border-t border-[#1f2d3a] text-[#b8c7d3]">
                <td className="px-3 py-2 font-mono text-[#d5e0ea]">{item.receiver_id}</td>
                <td className="px-3 py-2">{item.distance_m === null ? 'not reported' : `${item.distance_m.toFixed(1)} m`}</td>
                <td className="px-3 py-2">{item.delivery_status === 'not_reported' ? 'not reported' : eligible ? 'yes' : 'no'}</td>
                <td className="px-3 py-2">{item.delivery_status || 'not reported'}</td>
                <td className="px-3 py-2">{item.verification_status || 'not reported'}</td>
                <td className="max-w-64 px-3 py-2">{item.rejection_reason || '—'}</td>
                <td className="px-3 py-2">{item.safety ? item.safety.relevant ? 'relevant' : 'not relevant' : 'not reported'}</td>
                <td className="px-3 py-2">{item.safety ? item.safety.warning ? 'yes' : 'no' : 'not reported'}</td>
                <td className="px-3 py-2">{typeof item.processing_ms === 'number' && item.attempted_delivery ? `${item.processing_ms.toFixed(3)} ms` : 'not reported'}</td>
              </tr>
            })}</tbody>
          </table>
        </div>}
      </div>
    </details>
  </>
}
