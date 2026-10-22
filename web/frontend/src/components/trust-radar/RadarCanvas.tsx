import { useRef } from 'react'
import type { PointerEvent as ReactPointerEvent } from 'react'
import type { Vehicle } from '../../types'
import type { RadarAttackOverlay, RadarLayer, RadarPacket, RadarRecipient } from '../../types/trustRadar'
import { localRadarPosition } from '../../services/trustRadarData.mjs'

const SIZE = 480
const CENTER = SIZE / 2
const RADAR_RADIUS = CENTER - 42

export function RadarCanvas({
  vehicles,
  senderId,
  rangeM,
  recipients,
  packet,
  pulseKey,
  layer,
  redTeam,
  attack,
  onMove,
}: {
  vehicles: Vehicle[]
  senderId: string
  rangeM: number
  recipients: RadarRecipient[]
  packet: RadarPacket | null
  pulseKey: number
  layer: RadarLayer
  redTeam: boolean
  attack: RadarAttackOverlay | null
  onMove: (vehicleId: string, latitude: number, longitude: number) => void
}) {
  const draggedVehicle = useRef<string | null>(null)
  const sender = vehicles.find((vehicle) => vehicle.vehicle_id === senderId)
  const recipientById = new Map(recipients.map((item) => [item.receiver_id, item]))
  const eventPosition = packet?.message.position as { latitude?: number; longitude?: number } | undefined

  const commitDrag = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (!draggedVehicle.current || !sender) return
    const point = event.currentTarget.createSVGPoint()
    point.x = event.clientX
    point.y = event.clientY
    const local = point.matrixTransform(event.currentTarget.getScreenCTM()?.inverse())
    const eastM = (local.x - CENTER) * rangeM / RADAR_RADIUS
    const northM = (CENTER - local.y) * rangeM / RADAR_RADIUS
    const latitude = sender.position.latitude + northM / 111320
    const longitude = sender.position.longitude + eastM / (111320 * Math.max(0.01, Math.cos(sender.position.latitude * Math.PI / 180)))
    const id = draggedVehicle.current
    draggedVehicle.current = null
    onMove(id, latitude, longitude)
  }

  const announcement = `${vehicles.length} vehicles. ${recipients.length} recipient outcomes recorded.`

  return <div className="relative rounded-xl border border-slate-800 bg-[#0b1016] p-2 sm:p-4">
    <p className="sr-only" aria-live="polite">{announcement}</p>
    <div className="mb-2 flex items-center justify-between px-2 text-[10px] uppercase tracking-[0.2em] text-slate-500">
      <span>Local simulation radar</span><span>Range model · {rangeM.toLocaleString()} m</span>
    </div>
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      role="img"
      aria-label={`Vehicle radar centered on sender ${senderId}. Drag a vehicle marker to update its backend position.`}
      className="mx-auto block w-full max-w-[560px] touch-none"
      onPointerUp={commitDrag}
      onPointerCancel={() => { draggedVehicle.current = null }}
    >
      <defs>
        <pattern id="radar-grid" width="24" height="24" patternUnits="userSpaceOnUse">
          <path d="M 24 0 L 0 0 0 24" fill="none" stroke="#17232d" strokeWidth="0.7" />
        </pattern>
      </defs>
      <rect width={SIZE} height={SIZE} fill="url(#radar-grid)" />
      {[0.25, 0.5, 0.75].map((fraction) => <circle key={fraction} cx={CENTER} cy={CENTER} r={RADAR_RADIUS * fraction} fill="none" stroke="#1f2d3a" strokeWidth="1" />)}
      <circle cx={CENTER} cy={CENTER} r={RADAR_RADIUS} fill="none" stroke="#4c9be8" strokeWidth="1.5" strokeDasharray="5 5" />
      <line x1={CENTER - RADAR_RADIUS} y1={CENTER} x2={CENTER + RADAR_RADIUS} y2={CENTER} stroke="#263746" />
      <line x1={CENTER} y1={CENTER - RADAR_RADIUS} x2={CENTER} y2={CENTER + RADAR_RADIUS} stroke="#263746" />
      <text x={CENTER + RADAR_RADIUS - 4} y={CENTER - 7} textAnchor="end" fill="#6b7f90" fontSize="10" fontFamily="monospace">{rangeM} m</text>
      {pulseKey > 0 && <g key={pulseKey} aria-hidden="true">
        {[0, 1, 2].map((ring) => <circle key={ring} className="trust-radar-pulse" style={{ animationDelay: `${ring * 260}ms` }} cx={CENTER} cy={CENTER} r={RADAR_RADIUS} fill="none" stroke="#4c9be8" strokeWidth="1.5" />)}
      </g>}
      {eventPosition && Number.isFinite(eventPosition.latitude) && Number.isFinite(eventPosition.longitude) && sender && (() => {
        const event = { ...sender, position: { latitude: eventPosition.latitude as number, longitude: eventPosition.longitude as number } }
        const point = localRadarPosition(event, sender, rangeM, SIZE)
        return <g aria-label="Signed event location"><rect x={point.x - 6} y={point.y - 6} width="12" height="12" transform={`rotate(45 ${point.x} ${point.y})`} fill="#f5b942" stroke="#0b1016" /><text x={point.x + 11} y={point.y - 8} fill="#f5b942" fontSize="9" fontFamily="monospace">EVENT</text></g>
      })()}
      {vehicles.filter((vehicle) => vehicle.vehicle_id !== senderId).map((vehicle) => {
        if (!sender) return null
        const point = localRadarPosition(vehicle, sender, rangeM, SIZE)
        const outcome = recipientById.get(vehicle.vehicle_id)
        const attackApplies = redTeam && attack?.receiverId === vehicle.vehicle_id
        const failedGate = attackApplies ? attack.pipeline.find((step) => step.status === 'failed') : undefined
        const accepted = attackApplies ? attack?.accepted : outcome?.accepted
        const dropped = !attackApplies && outcome?.delivery_status === 'dropped'
        const outside = !attackApplies && outcome?.delivery_status === 'outside_range'
        const stroke = outside ? '#52606a' : dropped ? '#4c9be8' : accepted ? '#3ddc97' : failedGate ? '#ff5c5c' : '#6b7f90'
        const showRadio = layer === 'all' || layer === 'radio'
        const showCrypto = layer === 'all' || layer === 'crypto'
        const showSafety = layer === 'all' || layer === 'safety'
        const hasWarning = attackApplies ? Boolean(attack?.safety?.warning) : Boolean(outcome?.safety?.warning)
        const heading = vehicle.heading_degrees
        const tickX = typeof heading === 'number' ? Math.sin(heading * Math.PI / 180) * 12 : 0
        const tickY = typeof heading === 'number' ? -Math.cos(heading * Math.PI / 180) * 12 : 0
        const layerDim = (layer === 'radio' && !point.in_range) ||
          (layer === 'crypto' && !accepted && !failedGate) ||
          (layer === 'safety' && !outcome?.safety?.relevant && !hasWarning)
        const label = `${vehicle.vehicle_id}, ${point.distance_m?.toFixed(1) ?? 'unknown'} metres, ${outcome?.delivery_status ?? 'no delivery result'}, ${accepted ? 'verified' : 'not verified'}${hasWarning ? ', safety warning' : ''}`
        return <g
          key={vehicle.vehicle_id}
          role="img"
          aria-label={label}
          tabIndex={0}
          className={`cursor-grab outline-none focus-visible:opacity-100 ${layerDim ? 'opacity-35' : 'opacity-100'}`}
          onPointerDown={(event) => {
            if (event.button !== 0) return
            draggedVehicle.current = vehicle.vehicle_id
            event.currentTarget.ownerSVGElement?.setPointerCapture(event.pointerId)
          }}
          onKeyDown={(event) => { if (event.key === 'Enter') event.currentTarget.focus() }}
        >
          {showSafety && hasWarning && <circle cx={point.x} cy={point.y} r="21" fill="none" stroke="#f5b942" strokeWidth="2" />}
          {showRadio && dropped && <circle cx={point.x} cy={point.y} r="15" fill="none" stroke={stroke} strokeWidth="1.5" strokeDasharray="3 3" />}
          {typeof heading === 'number' && <line x1={point.x} y1={point.y} x2={point.x + tickX} y2={point.y + tickY} stroke={showCrypto ? stroke : '#4c9be8'} strokeWidth="2" />}
          <circle cx={point.x} cy={point.y} r="9" fill={dropped ? '#0b1016' : `${stroke}22`} stroke={showCrypto ? stroke : '#4c9be8'} strokeWidth="1.7" strokeDasharray={dropped || outside ? '3 2' : undefined} />
          {dropped && <g stroke="#4c9be8" strokeWidth="1.5"><line x1={point.x - 3} y1={point.y - 3} x2={point.x + 3} y2={point.y + 3} /><line x1={point.x + 3} y1={point.y - 3} x2={point.x - 3} y2={point.y + 3} /></g>}
          <text x={point.x + 14} y={point.y + 4} fill={showRadio && !point.in_range ? '#6b7f90' : '#d5e0ea'} fontSize="10" fontFamily="monospace">{vehicle.vehicle_id}</text>
        </g>
      })}
      {sender && <g aria-label={`Sender ${senderId}`}>
        <circle cx={CENTER} cy={CENTER} r="15" fill="#122638" stroke="#4c9be8" strokeWidth="2" />
        <path d={`M ${CENTER} ${CENTER - 7} L ${CENTER + 7} ${CENTER} L ${CENTER} ${CENTER + 7} L ${CENTER - 7} ${CENTER} Z`} fill="#4c9be8" />
        <text x={CENTER + 22} y={CENTER + 4} fill="#d5e0ea" fontSize="10" fontFamily="monospace">{senderId}</text>
      </g>}
    </svg>
    <div className="mt-1 flex flex-wrap justify-center gap-4 text-[10px] text-slate-500">
      <span><b className="text-[#4c9be8]">○</b> Radio delivery</span><span><b className="text-[#3ddc97]">●</b> Authenticated</span><span><b className="text-[#f5b942]">◇</b> Safety warning</span><span>Dashed + × dropped</span>
    </div>
  </div>
}
