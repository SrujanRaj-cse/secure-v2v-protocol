import { useState } from 'react'
import type { RadarPacket } from '../../types/trustRadar'

export function PacketAnatomy({
  packet,
  packetHash,
  tampered,
  disabled,
  receivers,
  selectedReceiver,
  onReceiverChange,
  onTamper,
}: {
  packet: RadarPacket | null
  packetHash: string | null
  tampered: boolean
  disabled: boolean
  receivers: string[]
  selectedReceiver: string
  onReceiverChange: (id: string) => void
  onTamper: (field: string, value: number, receiverId: string) => void
}) {
  const message = packet?.message ?? null
  const payload = message ? Object.fromEntries(Object.entries(message).filter(([key]) => !['timestamp', 'sequence_number'].includes(key))) : null
  const timestamp = typeof message?.timestamp === 'number' ? new Date(message.timestamp * 1000).toISOString() : 'not reported'
  const sequence = typeof message?.sequence_number === 'number' ? String(message.sequence_number) : 'not reported'
  const cert = packet?.certificate_pem
  const signature = packet?.signature_b64

  return <section className="rounded-xl border border-[#1f2d3a] bg-[#0e161e] p-4" aria-label="Signed packet anatomy">
    <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
      <div><h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-[#d5e0ea]">Packet anatomy</h2><p className="mt-1 text-[10px] text-[#6b7f90]">Segments are taken from the backend packet response.</p></div>
      {packetHash && <span className="font-mono text-[10px] text-[#6b7f90]">SHA-256 · {packetHash.slice(0, 24)}…</span>}
    </div>
    {!packet ? <p className="rounded-lg border border-dashed border-[#1f2d3a] p-5 text-center text-xs text-[#6b7f90]">Send a message to inspect its signed packet.</p> : <>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
        <Segment label="Payload" value={payload ? JSON.stringify(payload) : 'not reported'} />
        <Segment label="Timestamp" value={timestamp} />
        <Segment label="Sequence number" value={sequence} />
        <Segment label="Certificate" value={cert ? `${cert.split('\n')[0]} · ${cert.length} chars` : 'not reported'} />
        <Segment label="Signature" value={signature ? `${signature.slice(0, 18)}…${signature.slice(-10)}` : 'not reported'} danger={tampered} />
      </div>
      {tampered && <p role="status" className="mt-2 border-l-2 border-[#ff5c5c] bg-[#25151a] px-3 py-2 text-xs text-[#ff8c8c]">Backend modified the signed payload and kept the original signature. Receiver verification rejected it at the Signature gate.</p>}
      <TamperControls
        key={packetHash ?? 'packet'}
        message={packet.message}
        disabled={disabled}
        receivers={receivers}
        selectedReceiver={selectedReceiver}
        onReceiverChange={onReceiverChange}
        onTamper={onTamper}
      />
    </>}
  </section>
}

function TamperControls({
  message,
  disabled,
  receivers,
  selectedReceiver,
  onReceiverChange,
  onTamper,
}: {
  message: Record<string, unknown>
  disabled: boolean
  receivers: string[]
  selectedReceiver: string
  onReceiverChange: (id: string) => void
  onTamper: (field: string, value: number, receiverId: string) => void
}) {
  const [field, setField] = useState('speed')
  const defaultValue = (name: string) => {
    const current = message[name]
    return typeof current === 'number' ? String(name === 'speed' ? Math.min(400, current + 10) : Math.max(1, Math.floor(current) + 1)) : ''
  }
  const [newValue, setNewValue] = useState(() => defaultValue(field))
  const valid = newValue.trim() !== '' && Number.isFinite(Number(newValue)) && Number(newValue) >= (field === 'speed' ? 0 : 1) && (field !== 'speed' || Number(newValue) <= 400) && (field !== 'sequence_number' || Number.isInteger(Number(newValue)))
  return <div className="mt-3 flex flex-wrap items-end gap-2 border-t border-[#1f2d3a] pt-3">
    <label className="text-[10px] text-[#8fa2b2]">Tamper field<select value={field} onChange={(event) => { const next = event.target.value; setField(next); setNewValue(defaultValue(next)) }} className="mt-1 block rounded border border-[#1f2d3a] bg-[#0b1016] px-2 py-1.5 text-xs text-[#d5e0ea] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#4c9be8]"><option value="speed">speed</option><option value="sequence_number">sequence_number</option></select></label>
    <label className="text-[10px] text-[#8fa2b2]">New value<input type="number" value={newValue} min={field === 'speed' ? 0 : 1} max={field === 'speed' ? 400 : undefined} step={field === 'speed' ? 0.1 : 1} onChange={(event) => setNewValue(event.target.value)} className="mt-1 block w-32 rounded border border-[#1f2d3a] bg-[#0b1016] px-2 py-1.5 font-mono text-xs text-[#d5e0ea] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#4c9be8]" /></label>
    <label className="text-[10px] text-[#8fa2b2]">Receiver<select value={selectedReceiver} onChange={(event) => onReceiverChange(event.target.value)} className="mt-1 block rounded border border-[#1f2d3a] bg-[#0b1016] px-2 py-1.5 text-xs text-[#d5e0ea] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#4c9be8]">{receivers.map((id) => <option key={id}>{id}</option>)}</select></label>
    <button type="button" disabled={disabled || !valid} onClick={() => onTamper(field, Number(newValue), selectedReceiver)} className="rounded border border-[#7a3535] bg-[#241519] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-[#ff8c8c] hover:bg-[#30191f] focus-visible:outline focus-visible:outline-2 focus-visible:outline-white disabled:opacity-40">Tamper + resend</button>
  </div>
}

function Segment({ label, value, danger = false }: { label: string; value: string; danger?: boolean }) {
  return <div className={`min-w-0 rounded-md border px-3 py-2 ${danger ? 'border-[#8e3f45] bg-[#1d1218]' : 'border-[#1f2d3a] bg-[#0b1016]'}`}>
    <p className="text-[9px] uppercase tracking-[0.14em] text-[#6b7f90]">{label}</p><p className={`mt-1 break-all font-mono text-[10px] leading-4 ${danger ? 'text-[#ff8c8c]' : 'text-[#b8c7d3]'}`}>{value}</p>
  </div>
}
