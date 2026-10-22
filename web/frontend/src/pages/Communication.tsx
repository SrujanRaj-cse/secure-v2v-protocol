import { useEffect, useState } from 'react'
import { Radio, Send } from 'lucide-react'
import { api } from '../services/api'
import type { BroadcastResponse, SendMessageResponse } from '../types'
import { SecurityPipeline } from '../components/SecurityPipeline'
import { Alert } from '../components/AttackCard'
import { ErrorState } from '../components/MetricCard'

const MESSAGE_TYPES = ['Emergency Braking', 'Collision Warning', 'Road Hazard']
type Result = SendMessageResponse | BroadcastResponse

function isBroadcast(result: Result): result is BroadcastResponse {
  return 'recipients' in result
}

export function CommunicationPage() {
  const [mode, setMode] = useState<'broadcast' | 'unicast'>('broadcast')
  const [sender, setSender] = useState('A001')
  const [receiver, setReceiver] = useState('B001')
  const [vehicleIds, setVehicleIds] = useState(['A001', 'B001', 'C001'])
  const [event, setEvent] = useState('Emergency Braking')
  const [speed, setSpeed] = useState(80)
  const [latitude, setLatitude] = useState(17.385)
  const [longitude, setLongitude] = useState(78.4867)
  const [range, setRange] = useState(500)
  const [packetLoss, setPacketLoss] = useState(0)
  const [seed, setSeed] = useState(428)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getVehicles().then((items) => {
      const ids = items.map((vehicle) => vehicle.vehicle_id)
      if (ids.length) setVehicleIds(ids)
    }).catch(() => undefined)
  }, [])

  const handleSend = async () => {
    setLoading(true)
    setError(null)
    try {
      if (mode === 'broadcast') {
        await api.updateSimulationConfig({ communication_range_m: range, packet_loss_probability: packetLoss / 100, random_seed: seed })
        setResult(await api.broadcastMessage({ sender_id: sender, event, speed, latitude, longitude }))
      } else {
        setResult(await api.sendMessage({ sender_id: sender, receiver_id: receiver, event, speed, latitude, longitude }))
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Send failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white">Secure V2V Communication</h2>
        <p className="text-sm text-slate-500">In-process educational simulation using real certificate, signature, and replay checks. Default scene: B001 follows A001 northbound from about 100 m behind; a warning appears only when the signed event speed gives a TTC of 10 seconds or less.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-cyber-border bg-cyber-panel p-5">
          <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-slate-500">Message Parameters</h3>
          <div className="mb-4 flex rounded-lg border border-cyber-border p-1">
            {(['broadcast', 'unicast'] as const).map((value) => (
              <button key={value} type="button" onClick={() => setMode(value)} className={`flex-1 rounded-md px-3 py-2 text-xs uppercase ${mode === value ? 'bg-cyan-500/15 text-cyan-300' : 'text-slate-500'}`}>
                {value === 'broadcast' ? <><Radio className="mr-1 inline h-3 w-3" />Broadcast</> : 'Unicast'}
              </button>
            ))}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Sender">
              <select value={sender} onChange={(e) => setSender(e.target.value)} className="input">
                {vehicleIds.map((id) => <option key={id}>{id}</option>)}
              </select>
            </Field>
            {mode === 'unicast' && <Field label="Receiver">
              <select value={receiver} onChange={(e) => setReceiver(e.target.value)} className="input">
                {vehicleIds.map((id) => <option key={id}>{id}</option>)}
              </select>
            </Field>}
            <Field label="Safety Event" className="sm:col-span-2">
              <select value={event} onChange={(e) => setEvent(e.target.value)} className="input">
                {MESSAGE_TYPES.map((item) => <option key={item}>{item}</option>)}
              </select>
            </Field>
            <Field label="Speed (km/h)"><input type="number" min="0" max="400" value={speed} onChange={(e) => setSpeed(Number(e.target.value))} className="input" /></Field>
            <Field label="Latitude"><input type="number" min="-90" max="90" step="0.0001" value={latitude} onChange={(e) => setLatitude(Number(e.target.value))} className="input" /></Field>
            <Field label="Longitude"><input type="number" min="-180" max="180" step="0.0001" value={longitude} onChange={(e) => setLongitude(Number(e.target.value))} className="input" /></Field>
            {mode === 'broadcast' && <>
              <Field label="Communication range (m)"><input type="number" min="0" max="100000" value={range} onChange={(e) => setRange(Number(e.target.value))} className="input" /></Field>
              <Field label="Packet loss (%)"><input type="number" min="0" max="100" step="1" value={packetLoss} onChange={(e) => setPacketLoss(Number(e.target.value))} className="input" /></Field>
              <Field label="Reproducible seed"><input type="number" min="0" value={seed} onChange={(e) => setSeed(Number(e.target.value))} className="input" /></Field>
            </>}
          </div>
          <button type="button" onClick={handleSend} disabled={loading || (mode === 'unicast' && sender === receiver)} className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-500/10 py-3 text-sm font-semibold uppercase tracking-wider text-cyber-accent ring-1 ring-cyan-500/30 hover:bg-cyan-500/20 disabled:opacity-50">
            <Send className="h-4 w-4" />{loading ? 'Sending...' : mode === 'broadcast' ? 'Sign once and broadcast' : 'Send Secure Message'}
          </button>
        </div>

        <div className="space-y-3">
          {error && <ErrorState message={error} />}
          {result && <>
            <p className="font-mono text-xs text-slate-500">SHA-256: {result.message_hash}</p>
            {isBroadcast(result) ? <BroadcastResults result={result} /> : <>
              <Alert accepted={result.accepted} reason={result.reason} mechanism={result.accepted ? 'Full verification pipeline' : 'Security validation failed'} />
              <SecurityPipeline steps={result.pipeline} />
            </>}
          </>}
          {!result && !error && <div className="rounded-xl border border-dashed border-cyber-border p-8 text-center text-sm text-slate-500">Send a message to see delivery and verification outcomes.</div>}
        </div>
      </div>
    </div>
  )
}

function BroadcastResults({ result }: { result: BroadcastResponse }) {
  return <div className="overflow-hidden rounded-xl border border-cyber-border bg-cyber-panel">
    <div className="border-b border-cyber-border p-4">
      <h3 className="text-sm font-semibold text-white">Broadcast deliveries</h3>
      <p className="mt-1 text-xs text-slate-500">Message {result.message_id} · one signature · {result.range_m} m range · seed {result.seed}</p>
    </div>
    <div className="overflow-x-auto"><table className="w-full text-left text-xs">
      <thead className="bg-slate-900/60 text-slate-500"><tr><th className="p-3">Vehicle</th><th className="p-3">Distance</th><th className="p-3">Delivery</th><th className="p-3">Verification</th><th className="p-3">Safety evaluation</th></tr></thead>
      <tbody>{result.recipients.map((item) => <tr key={item.receiver_id} className="border-t border-cyber-border/70">
        <td className="p-3 font-mono text-white">{item.receiver_id}</td>
        <td className="p-3 text-slate-400">{item.distance_m === null ? '—' : `${item.distance_m.toFixed(1)} m`}</td>
        <td className="p-3 text-slate-300">{item.delivery_status}{item.attempted_delivery ? ' (attempted)' : ''}</td>
        <td className={`p-3 ${item.accepted ? 'text-emerald-400' : 'text-amber-300'}`}>{item.verification_status}{item.rejection_reason ? `: ${item.rejection_reason}` : ''}</td>
        <td className="p-3 text-slate-400">{item.safety ? `${item.safety_status}: ${item.safety.reason}${item.safety.ttc_seconds === null ? '' : ` · TTC ${item.safety.ttc_seconds}s`}` : 'Not run'}</td>
      </tr>)}</tbody>
    </table></div>
  </div>
}

function Field({ label, children, className = '' }: { label: string; children: React.ReactNode; className?: string }) {
  return <label className={`block ${className}`}><span className="mb-1 block text-xs text-slate-500">{label}</span>{children}</label>
}
