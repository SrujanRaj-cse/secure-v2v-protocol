import { useState } from 'react'
import { Send } from 'lucide-react'
import { api } from '../services/api'
import type { SendMessageResponse } from '../types'
import { SecurityPipeline } from '../components/SecurityPipeline'
import { Alert } from '../components/AttackCard'
import { ErrorState } from '../components/MetricCard'

const MESSAGE_TYPES = [
  'Emergency Braking',
  'Collision Warning',
  'Speed Update',
  'Position Update',
  'Accident Warning',
  'Road Hazard',
]

export function CommunicationPage() {
  const [sender, setSender] = useState('A001')
  const [receiver, setReceiver] = useState('B001')
  const [event, setEvent] = useState('Emergency Braking')
  const [speed, setSpeed] = useState(80)
  const [latitude, setLatitude] = useState(17.385)
  const [longitude, setLongitude] = useState(78.4867)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SendMessageResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSend = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.sendMessage({
        sender_id: sender,
        receiver_id: receiver,
        event,
        speed,
        latitude,
        longitude,
      })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Send failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white">
          Secure V2V Communication
        </h2>
        <p className="text-sm text-slate-500">
          Send a signed safety message through the real security pipeline
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-cyber-border bg-cyber-panel p-5">
          <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-slate-500">
            Message Parameters
          </h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Sender">
              <select
                value={sender}
                onChange={(e) => setSender(e.target.value)}
                className="input"
              >
                <option value="A001">A001</option>
                <option value="B001">B001</option>
                <option value="C001">C001</option>
              </select>
            </Field>
            <Field label="Receiver">
              <select
                value={receiver}
                onChange={(e) => setReceiver(e.target.value)}
                className="input"
              >
                <option value="A001">A001</option>
                <option value="B001">B001</option>
                <option value="C001">C001</option>
              </select>
            </Field>
            <Field label="Message Type" className="sm:col-span-2">
              <select
                value={event}
                onChange={(e) => setEvent(e.target.value)}
                className="input"
              >
                {MESSAGE_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Speed (km/h)">
              <input
                type="number"
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
                className="input"
              />
            </Field>
            <Field label="Latitude">
              <input
                type="number"
                step="0.0001"
                value={latitude}
                onChange={(e) => setLatitude(Number(e.target.value))}
                className="input"
              />
            </Field>
            <Field label="Longitude">
              <input
                type="number"
                step="0.0001"
                value={longitude}
                onChange={(e) => setLongitude(Number(e.target.value))}
                className="input"
              />
            </Field>
          </div>
          <button
            type="button"
            onClick={handleSend}
            disabled={loading || sender === receiver}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-500/10 py-3 text-sm font-semibold uppercase tracking-wider text-cyber-accent ring-1 ring-cyan-500/30 hover:bg-cyan-500/20 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            {loading ? 'Sending...' : 'Send Secure Message'}
          </button>
        </div>

        <div>
          {error && <ErrorState message={error} />}
          {result && (
            <>
              <Alert
                accepted={result.accepted}
                reason={result.reason}
                mechanism={
                  result.accepted
                    ? 'Full verification pipeline'
                    : 'Security validation failed'
                }
              />
              {result.message_hash && (
                <p className="mb-3 mt-2 font-mono text-xs text-slate-500">
                  SHA-256: {result.message_hash}
                </p>
              )}
            </>
          )}
          {result?.pipeline && (
            <SecurityPipeline steps={result.pipeline} />
          )}
          {!result && !error && (
            <div className="rounded-xl border border-dashed border-cyber-border p-8 text-center text-sm text-slate-500">
              Send a message to see the security pipeline
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Field({
  label,
  children,
  className = '',
}: {
  label: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1 block text-xs text-slate-500">{label}</span>
      {children}
    </label>
  )
}
