import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../services/api'
import type { AttackResponse, BroadcastRecipient, PipelineStep, SendMessageResponse, SimulationConfig, Vehicle, VerificationGate } from '../types'
import type { RadarAttackOverlay, RadarLayer, RadarPacket, RadarRecipient } from '../types/trustRadar'
import { countRadarRecipients, gatesFromPipeline, localRadarPosition } from '../services/trustRadarData.mjs'
import { RadarCanvas } from '../components/trust-radar/RadarCanvas'
import { VerificationRails } from '../components/trust-radar/VerificationRails'
import { PacketAnatomy } from '../components/trust-radar/PacketAnatomy'
import { ResultsDrawer } from '../components/trust-radar/ResultsDrawer'

const TIMELINE = ['Sign', 'Deliver', 'Verify', 'Warn', 'Done']
const EVENTS = ['Emergency Braking', 'Road Hazard', 'Collision Warning']

interface RadarActivity {
  mode: 'broadcast' | 'unicast'
  recipients: RadarRecipient[]
  packet: RadarPacket | null
  hash: string | null
}

function verificationStatus(pipeline: PipelineStep[], accepted: boolean) {
  if (accepted) return 'accepted'
  const failed = pipeline.find((step) => step.status === 'failed')
  const stage = failed?.name.toLowerCase() ?? ''
  if (stage.includes('message validation')) return 'invalid_schema'
  if (stage.includes('certificate') || stage.includes('identity')) return 'invalid_certificate'
  if (stage.includes('signature')) return 'invalid_signature'
  if (stage.includes('timestamp')) return 'stale'
  if (stage.includes('replay') || stage.includes('sequence')) return 'replayed'
  return 'rejected'
}

function recipientFromBroadcast(item: BroadcastRecipient): RadarRecipient {
  return {
    ...item,
    verification_ms: item.verification_ms ?? null,
    processing_ms: item.processing_ms ?? null,
    verification_gates: item.verification_gates ?? gatesFromPipeline(),
  }
}

function mapUnicast(result: SendMessageResponse, receiver: Vehicle | undefined, rangeM: number): RadarRecipient[] {
  const position = result.packet.message.position as { latitude: number; longitude: number } | undefined
  const distance = position && receiver ? localRadarPosition(receiver, { position }, rangeM).distance_m : null
  const accepted = result.accepted
  const safetyStatus: VerificationGate['status'] = 'not_reported'
  return [{
    receiver_id: receiver?.vehicle_id ?? 'not reported',
    message_id: typeof result.packet.message.message_id === 'string' ? result.packet.message.message_id : 'not reported',
    distance_m: distance,
    delivery_status: 'delivered',
    attempted_delivery: true,
    verification_status: verificationStatus(result.pipeline, accepted),
    safety_status: 'not_reported',
    accepted,
    rejection_reason: accepted ? null : result.reason,
    processing_ms: null,
    verification_ms: null,
    safety_evaluation_performed: false,
    safety: null,
    verification_gates: gatesFromPipeline(result.pipeline, safetyStatus, 'Unicast endpoint does not report relevance.'),
  }]
}

export function TrustRadarPage() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [config, setConfig] = useState<SimulationConfig | null>(null)
  const [initialLoading, setInitialLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<'broadcast' | 'unicast'>('broadcast')
  const [senderId, setSenderId] = useState('A001')
  const [receiverId, setReceiverId] = useState('B001')
  const [event, setEvent] = useState('Emergency Braking')
  const [range, setRange] = useState('500')
  const [lossPercent, setLossPercent] = useState('0')
  const [seed, setSeed] = useState('428')
  const [activity, setActivity] = useState<RadarActivity | null>(null)
  const [attack, setAttack] = useState<RadarAttackOverlay | null>(null)
  const [attackMessage, setAttackMessage] = useState<AttackResponse | null>(null)
  const [redTeam, setRedTeam] = useState(false)
  const [layer, setLayer] = useState<RadarLayer>('all')
  const [pulseKey, setPulseKey] = useState(0)
  const [phase, setPhase] = useState(0)
  const [autoPlayKey, setAutoPlayKey] = useState(0)
  const [positionVehicleId, setPositionVehicleId] = useState('B001')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [movementBusy, setMovementBusy] = useState(false)
  const animationTimer = useRef<number | null>(null)

  const sender = vehicles.find((vehicle) => vehicle.vehicle_id === senderId)
  const receiver = vehicles.find((vehicle) => vehicle.vehicle_id === receiverId)
  const selectedPositionVehicle = vehicles.find((vehicle) => vehicle.vehicle_id === positionVehicleId)
  const recipients = activity?.recipients ?? []
  const countSummary = countRadarRecipients(recipients)
  const receiverIds = vehicles.filter((vehicle) => vehicle.vehicle_id !== senderId).map((vehicle) => vehicle.vehicle_id)
  const reduceMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  const replaceVehicle = useCallback((updated: Vehicle) => {
    setVehicles((current) => current.map((vehicle) => vehicle.vehicle_id === updated.vehicle_id ? updated : vehicle))
  }, [])

  useEffect(() => {
    let live = true
    Promise.all([api.getVehicles(), api.getSimulationConfig()]).then(([items, settings]) => {
      if (!live) return
      setVehicles(items)
      setConfig(settings)
      setRange(String(settings.communication_range_m))
      setLossPercent(String(settings.packet_loss_probability * 100))
      setSeed(String(settings.random_seed))
      if (items.length) {
        if (!items.some((vehicle) => vehicle.vehicle_id === senderId)) setSenderId(items[0].vehicle_id)
        if (!items.some((vehicle) => vehicle.vehicle_id === receiverId)) setReceiverId(items.find((vehicle) => vehicle.vehicle_id !== senderId)?.vehicle_id ?? items[0].vehicle_id)
        if (!items.some((vehicle) => vehicle.vehicle_id === positionVehicleId)) setPositionVehicleId(items.find((vehicle) => vehicle.vehicle_id !== senderId)?.vehicle_id ?? items[0].vehicle_id)
      }
      setInitialLoading(false)
    }).catch((cause: unknown) => {
      if (!live) return
      setError(cause instanceof Error ? cause.message : 'Backend unavailable. Start the FastAPI service and retry.')
      setInitialLoading(false)
    })
    return () => { live = false }
  // Initial defaults are only used to choose IDs; server state remains authoritative.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (selectedPositionVehicle) {
      setLatitude(String(selectedPositionVehicle.position.latitude))
      setLongitude(String(selectedPositionVehicle.position.longitude))
    }
  }, [selectedPositionVehicle])

  useEffect(() => {
    if (!autoPlayKey || reduceMotion) return
    let next = 0
    const timer = window.setInterval(() => {
      next += 1
      setPhase(next)
      if (next >= TIMELINE.length - 1) window.clearInterval(timer)
    }, 340)
    animationTimer.current = timer
    return () => {
      window.clearInterval(timer)
      animationTimer.current = null
    }
  }, [autoPlayKey, reduceMotion])

  const startVisualReplay = () => {
    setPulseKey((key) => key + 1)
    setPhase(reduceMotion ? TIMELINE.length - 1 : 0)
    if (!reduceMotion) setAutoPlayKey((key) => key + 1)
  }

  const validateControls = () => {
    const rangeValue = Number(range)
    const lossValue = Number(lossPercent)
    const seedValue = Number(seed)
    if (!range.trim() || !Number.isFinite(rangeValue) || rangeValue < 0 || rangeValue > 100000) return 'Range must be between 0 and 100,000 metres.'
    if (!lossPercent.trim() || !Number.isFinite(lossValue) || lossValue < 0 || lossValue > 100) return 'Packet loss must be between 0 and 100 percent.'
    if (!seed.trim() || !Number.isInteger(seedValue) || seedValue < 0 || seedValue > 2147483647) return 'Seed must be a non-negative 32-bit integer.'
    if (!sender) return 'Select an available sender vehicle.'
    if (mode === 'unicast' && (!receiver || receiver.vehicle_id === senderId)) return 'Choose a receiver different from the sender.'
    return null
  }

  const send = async () => {
    const invalid = validateControls()
    if (invalid) { setError(invalid); return }
    setBusy(true)
    setError(null)
    setActivity(null)
    setAttack(null)
    setAttackMessage(null)
    try {
      const rangeValue = Number(range)
      if (mode === 'broadcast') {
        const updatedConfig = await api.updateSimulationConfig({ communication_range_m: rangeValue, packet_loss_probability: Number(lossPercent) / 100, random_seed: Number(seed) })
        setConfig(updatedConfig)
        const result = await api.broadcastMessage({ sender_id: senderId, event, range_m: rangeValue, packet_loss_probability: Number(lossPercent) / 100 })
        setActivity({ mode, recipients: result.recipients.map(recipientFromBroadcast), packet: result.packet, hash: result.message_hash })
      } else {
        const result = await api.sendMessage({ sender_id: senderId, receiver_id: receiverId, event })
        setActivity({ mode, recipients: mapUnicast(result, receiver, rangeValue), packet: result.packet, hash: result.message_hash })
      }
      startVisualReplay()
    } catch (cause) {
      setActivity(null)
      setError(cause instanceof Error ? cause.message : 'The request failed. Check the backend and try again.')
    } finally { setBusy(false) }
  }

  const runAttack = async (kind: 'replay' | 'impersonation' | 'fake-certificate' | 'stale' | 'false-data', targetReceiver = receiverId) => {
    setBusy(true)
    setError(null)
    setAttack(null)
    setAttackMessage(null)
    try {
      let result: AttackResponse
      if (kind === 'replay') result = await api.attackReplay(targetReceiver)
      else if (kind === 'impersonation') result = await api.attackImpersonation(senderId, targetReceiver)
      else if (kind === 'fake-certificate') result = await api.attackFakeCertificate(targetReceiver)
      else if (kind === 'stale') result = await api.attackStale(targetReceiver)
      else result = await api.attackFalseData(targetReceiver)
      setAttackMessage(result)
      setAttack({ receiverId: targetReceiver, accepted: result.accepted, reason: result.reason, pipeline: result.pipeline, safety: result.safety, kind })
      if (result.packet) setActivity((current) => current ? { ...current, packet: result.packet as RadarPacket, hash: null } : { mode: 'unicast', recipients: [], packet: result.packet as RadarPacket, hash: null })
      setPhase(TIMELINE.length - 1)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Attack simulation failed.')
    } finally { setBusy(false) }
  }

  const tamper = async (field: string, value: number, targetReceiver: string) => {
    if (!activity?.packet) return
    setBusy(true)
    setError(null)
    setAttack(null)
    setAttackMessage(null)
    try {
      const result = await api.attackTampering(field, value, targetReceiver)
      setAttackMessage(result)
      setAttack({ receiverId: targetReceiver, accepted: result.accepted, reason: result.reason, pipeline: result.pipeline, kind: 'tampering' })
      if (result.packet) setActivity((current) => current ? { ...current, packet: result.packet as RadarPacket, hash: null } : current)
      setPhase(TIMELINE.length - 1)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Tamper simulation failed.') }
    finally { setBusy(false) }
  }

  const savePosition = async (vehicleId: string, requestedLatitude?: number, requestedLongitude?: number) => {
    const lat = requestedLatitude ?? (latitude.trim() ? Number(latitude) : Number.NaN)
    const lon = requestedLongitude ?? (longitude.trim() ? Number(longitude) : Number.NaN)
    if (!Number.isFinite(lat) || lat < -90 || lat > 90 || !Number.isFinite(lon) || lon < -180 || lon > 180) {
      setError('Coordinates must be valid decimal latitude and longitude.'); return
    }
    setMovementBusy(true)
    setError(null)
    try { replaceVehicle(await api.updateVehicle(vehicleId, { latitude: lat, longitude: lon })) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to update vehicle position.') }
    finally { setMovementBusy(false) }
  }

  const advance = async () => {
    setMovementBusy(true)
    setError(null)
    try { setVehicles(await api.advanceSimulation(1)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to advance vehicle simulation.') }
    finally { setMovementBusy(false) }
  }

  const selectedRange = Number(range) || config?.communication_range_m || 500
  const inFlightName = mode === 'broadcast' ? 'Broadcast' : 'Unicast'

  return <div className={`mx-auto max-w-[1500px] space-y-4 ${redTeam ? 'trust-radar-red rounded-xl border border-[#4c272d] bg-[#100d12] p-3' : ''}`}>
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[#1f2d3a] pb-3">
      <div><p className="font-mono text-[10px] uppercase tracking-[0.24em] text-[#4c9be8]">Secure V2V · Monitor</p><h1 className="text-xl font-semibold tracking-wide text-[#d5e0ea]">Trust radar</h1></div>
      <div className="flex flex-wrap items-center gap-2">
        <div role="group" aria-label="Communication mode" className="flex rounded-md border border-[#1f2d3a] p-1">
          {(['broadcast', 'unicast'] as const).map((item) => <button key={item} type="button" aria-pressed={mode === item} onClick={() => setMode(item)} className={`rounded px-3 py-1.5 text-[10px] uppercase tracking-wider focus-visible:outline focus-visible:outline-2 focus-visible:outline-white ${mode === item ? 'bg-[#172a3a] text-[#7db7ed]' : 'text-[#6b7f90] hover:text-[#d5e0ea]'}`}>{item}</button>)}
        </div>
        <div role="group" aria-label="Layer filter" className="flex gap-1">
          {(['radio', 'crypto', 'safety'] as const).map((item) => <button key={item} type="button" aria-pressed={layer === item} onClick={() => setLayer(layer === item ? 'all' : item)} className={`rounded border px-2.5 py-1.5 text-[9px] uppercase tracking-wider focus-visible:outline focus-visible:outline-2 focus-visible:outline-white ${layer === item ? layerButtonClass(item) : 'border-[#1f2d3a] text-[#6b7f90] hover:text-[#d5e0ea]'}`}>{item}</button>)}
        </div>
        <button type="button" role="switch" aria-checked={redTeam} onClick={() => setRedTeam((value) => !value)} className={`rounded border px-3 py-1.5 text-[10px] uppercase tracking-wider focus-visible:outline focus-visible:outline-2 focus-visible:outline-white ${redTeam ? 'border-[#ff5c5c] bg-[#25151a] text-[#ff8c8c]' : 'border-[#1f2d3a] text-[#8fa2b2]'}`}>{redTeam ? 'Red team on' : 'Red team'}</button>
      </div>
    </header>

    {error && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 border border-[#7a3535] bg-[#211318] px-4 py-3 text-xs text-[#ff9c9c]"><span>{error}</span><button type="button" onClick={() => { setError(null); setInitialLoading(true); Promise.all([api.getVehicles(), api.getSimulationConfig()]).then(([items, settings]) => { setVehicles(items); setConfig(settings); setInitialLoading(false) }).catch((cause: unknown) => { setError(cause instanceof Error ? cause.message : 'Backend unavailable'); setInitialLoading(false) }) }} className="rounded border border-[#7a3535] px-3 py-1.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white">Retry backend</button></div>}

    <section className="grid gap-3 rounded-xl border border-[#1f2d3a] bg-[#0e161e] p-3 md:grid-cols-2 xl:grid-cols-[1fr_1fr_1.1fr_1.1fr_1fr_0.8fr_auto]" aria-label="Broadcast controls">
      <SelectField label="Sender" value={senderId} onChange={setSenderId} options={vehicles.map((vehicle) => vehicle.vehicle_id)} disabled={initialLoading} />
      {mode === 'unicast' && <SelectField label="Receiver" value={receiverId} onChange={setReceiverId} options={receiverIds} disabled={initialLoading} />}
      <SelectField label="Event" value={event} onChange={setEvent} options={EVENTS} disabled={initialLoading} />
      <NumberField label="Range · metres" value={range} min={0} max={100000} onChange={setRange} />
      <NumberField label="Packet loss · %" value={lossPercent} min={0} max={100} step={1} onChange={setLossPercent} />
      <NumberField label="Seed" value={seed} min={0} max={2147483647} step={1} onChange={setSeed} />
      <button type="button" onClick={send} disabled={initialLoading || busy || !config || Boolean(validateControls())} className="min-h-10 rounded bg-[#18334a] px-4 text-xs font-bold uppercase tracking-wide text-[#9bcdf7] hover:bg-[#214665] focus-visible:outline focus-visible:outline-2 focus-visible:outline-white disabled:opacity-40">{busy ? 'Working…' : inFlightName}</button>
    </section>

    {initialLoading && <p role="status" className="border border-[#1f2d3a] bg-[#0e161e] px-4 py-6 text-center text-sm text-[#8fa2b2]">Connecting to the simulation backend…</p>}
    {!initialLoading && !vehicles.length && <p className="border border-dashed border-[#1f2d3a] px-4 py-8 text-center text-sm text-[#8fa2b2]">The backend returned no vehicles. Register vehicles in the simulation before sending a message.</p>}

    {!initialLoading && vehicles.length > 0 && <>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.08fr)_minmax(460px,0.92fr)]">
        <RadarCanvas vehicles={vehicles} senderId={senderId} rangeM={selectedRange} recipients={recipients} packet={activity?.packet ?? null} pulseKey={pulseKey} layer={layer} redTeam={redTeam} attack={attack} onMove={savePosition} />
        <VerificationRails recipientVehicles={vehicles.filter((vehicle) => vehicle.vehicle_id !== senderId)} recipients={recipients} attack={attack} phase={activity ? phase : 0} />
      </div>

      {redTeam && <RedTeamPanel receiverIds={receiverIds} selectedReceiver={receiverId} onReceiverChange={setReceiverId} onAttack={runAttack} attack={attackMessage} busy={busy} hasPacket={Boolean(activity?.packet)} />}
      {attackMessage?.attack === 'false_data' && attackMessage.accepted && attackMessage.plausibility_suspicious && <div role="status" className="border border-[#8e7239] bg-[#211d13] px-4 py-3 text-sm font-semibold text-[#f5b942]">Authentic is not the same as truthful. <span className="font-normal">The backend accepted the signature and reported: {attackMessage.plausibility_flags?.join('; ') || 'plausibility concerns'}.</span></div>}

      <PacketAnatomy packet={activity?.packet ?? null} packetHash={activity?.hash ?? null} tampered={attack?.kind === 'tampering' && attack.pipeline.some((step) => step.name === 'Signature Verification' && step.status === 'failed')} disabled={busy || !activity?.packet} receivers={receiverIds} selectedReceiver={receiverId} onReceiverChange={setReceiverId} onTamper={tamper} />

      {activity && <section className="flex flex-wrap items-center gap-3 rounded-xl border border-[#1f2d3a] bg-[#0e161e] px-4 py-3" aria-label="Recorded message timeline">
        <span className="text-[10px] uppercase tracking-[0.15em] text-[#6b7f90]">Visual replay of recorded results</span>
        <input aria-label="Timeline step" type="range" min={0} max={TIMELINE.length - 1} step={1} value={phase} onChange={(event) => { if (animationTimer.current) window.clearInterval(animationTimer.current); setAutoPlayKey(0); setPhase(Number(event.target.value)) }} className="min-w-36 flex-1 accent-[#4c9be8]" />
        {TIMELINE.map((step, index) => <button key={step} type="button" aria-pressed={phase === index} onClick={() => { if (animationTimer.current) window.clearInterval(animationTimer.current); setAutoPlayKey(0); setPhase(index) }} className={`rounded px-1.5 py-1 text-[9px] uppercase focus-visible:outline focus-visible:outline-2 focus-visible:outline-white ${phase === index ? 'text-[#9bcdf7]' : 'text-[#526576]'}`}>{step}</button>)}
        {phase === 4 && <span className="ml-auto font-mono text-[10px] text-[#6b7f90]">{countSummary.delivered}/{countSummary.eligible} delivered · reported processing time is shown in the table</span>}
      </section>}

      <section className="grid gap-3 rounded-xl border border-[#1f2d3a] bg-[#0e161e] p-4 md:grid-cols-[1fr_auto_auto] md:items-end" aria-label="Backend vehicle placement controls">
        <div className="grid gap-2 sm:grid-cols-3">
          <SelectField label="Place vehicle" value={positionVehicleId} onChange={setPositionVehicleId} options={vehicles.map((vehicle) => vehicle.vehicle_id)} disabled={movementBusy} />
          <NumberField label="Latitude" value={latitude} min={-90} max={90} step={0.000001} onChange={setLatitude} />
          <NumberField label="Longitude" value={longitude} min={-180} max={180} step={0.000001} onChange={setLongitude} />
        </div>
        <button type="button" disabled={movementBusy || !positionVehicleId} onClick={() => savePosition(positionVehicleId)} className="rounded border border-[#1f2d3a] px-3 py-2 text-[10px] uppercase text-[#8fa2b2] hover:text-[#d5e0ea] focus-visible:outline focus-visible:outline-2 focus-visible:outline-white disabled:opacity-40">{movementBusy ? 'Updating…' : 'Save position to backend'}</button>
        <button type="button" disabled={movementBusy} onClick={advance} className="rounded border border-[#1f2d3a] px-3 py-2 text-[10px] uppercase text-[#8fa2b2] hover:text-[#d5e0ea] focus-visible:outline focus-visible:outline-2 focus-visible:outline-white disabled:opacity-40">Advance simulation · 1 s</button>
        <p className="text-[10px] text-[#6b7f90] md:col-span-3">Drag a vehicle marker or edit coordinates; changes are sent to the backend. The radar uses a local flat projection. The configured ring is a range model, not DSRC/C-V2X coverage.</p>
      </section>

      <ResultsDrawer recipients={recipients} />
    </>}
  </div>
}

function RedTeamPanel({ receiverIds, selectedReceiver, onReceiverChange, onAttack, attack, busy, hasPacket }: {
  receiverIds: string[]; selectedReceiver: string; onReceiverChange: (id: string) => void
  onAttack: (kind: 'replay' | 'impersonation' | 'fake-certificate' | 'stale' | 'false-data', receiver?: string) => void
  attack: AttackResponse | null; busy: boolean; hasPacket: boolean
}) {
  const choices: Array<{ kind: 'replay' | 'impersonation' | 'fake-certificate' | 'stale' | 'false-data'; label: string }> = [
    { kind: 'replay', label: 'Replay last packet' }, { kind: 'impersonation', label: 'Untrusted certificate' },
    { kind: 'fake-certificate', label: 'Swapped certificate' }, { kind: 'stale', label: 'Stale signed message' }, { kind: 'false-data', label: 'False data' },
  ]
  const failedStage = attack?.pipeline.find((step) => step.status === 'failed')
  return <section className="rounded-xl border border-[#73363d] bg-[#151116] p-4" aria-label="Red team attack simulations">
    <div className="mb-3 flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-sm font-semibold uppercase tracking-[0.15em] text-[#ff8c8c]">Red team · local simulation</h2><p className="mt-1 text-[10px] text-[#9a7479]">Attack outcomes come from the existing backend verification routes.</p></div>
      <label className="text-[10px] text-[#9a7479]">Receiver<select value={selectedReceiver} onChange={(event) => onReceiverChange(event.target.value)} className="ml-2 rounded border border-[#553036] bg-[#0b1016] px-2 py-1.5 text-xs text-[#d5e0ea] focus-visible:outline focus-visible:outline-2 focus-visible:outline-white">{receiverIds.map((id) => <option key={id}>{id}</option>)}</select></label>
    </div>
    <div className="flex flex-wrap gap-2">{choices.map(({ kind, label }) => <button key={kind} type="button" disabled={busy || (['replay', 'fake-certificate'].includes(kind) && !hasPacket)} onClick={() => onAttack(kind, selectedReceiver)} className="rounded border border-[#553036] px-3 py-2 text-[10px] uppercase text-[#e59aa1] hover:bg-[#28181d] focus-visible:outline focus-visible:outline-2 focus-visible:outline-white disabled:opacity-40">{label}</button>)}</div>
    <p className="mt-2 text-[10px] text-[#805f64]">Replay and certificate-swap flows need a previously signed message. Receiver replay state is independent: an accepted original broadcast at another receiver remains accepted while this repeated delivery is rejected.</p>
    {attack && <p role="status" className="mt-3 border-l-2 border-[#ff5c5c] pl-3 text-xs text-[#d5e0ea]">{attack.accepted ? 'Message accepted' : `Rejected at ${failedStage?.name ?? 'reported verification stage'}`}: {attack.reason}</p>}
  </section>
}

function SelectField({ label, value, options, onChange, disabled = false }: { label: string; value: string; options: string[]; onChange: (value: string) => void; disabled?: boolean }) {
  return <label className="min-w-0 text-[9px] uppercase tracking-[0.13em] text-[#6b7f90]">{label}<select value={value} disabled={disabled || options.length === 0} onChange={(event) => onChange(event.target.value)} className="mt-1 block w-full rounded border border-[#1f2d3a] bg-[#0b1016] px-2 py-2 text-xs normal-case tracking-normal text-[#d5e0ea] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#4c9be8] disabled:opacity-40">{options.map((option) => <option key={option}>{option}</option>)}</select></label>
}

function NumberField({ label, value, min, max, step, onChange }: { label: string; value: string; min: number; max: number; step?: number; onChange: (value: string) => void }) {
  const numeric = Boolean(value.trim()) && Number.isFinite(Number(value)) && Number(value) >= min && Number(value) <= max
  return <label className="min-w-0 text-[9px] uppercase tracking-[0.13em] text-[#6b7f90]">{label}<input type="number" inputMode="decimal" value={value} min={min} max={max} step={step} aria-invalid={!numeric} onChange={(event) => onChange(event.target.value)} className={`mt-1 block w-full rounded border bg-[#0b1016] px-2 py-2 font-mono text-xs text-[#d5e0ea] focus-visible:outline focus-visible:outline-2 ${numeric ? 'border-[#1f2d3a] focus-visible:outline-[#4c9be8]' : 'border-[#ff5c5c] focus-visible:outline-[#ff5c5c]'}`} /></label>
}

function layerButtonClass(layer: Exclude<RadarLayer, 'all'>) {
  if (layer === 'radio') return 'border-[#4c9be8] bg-[#14243a] text-[#85baf0]'
  if (layer === 'crypto') return 'border-[#3ddc97] bg-[#12251e] text-[#72eab4]'
  return 'border-[#f5b942] bg-[#282114] text-[#f5b942]'
}
