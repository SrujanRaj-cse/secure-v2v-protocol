export const RADAR_GATE_NAMES = ['Schema', 'Certificate', 'Signature', 'Freshness', 'Replay', 'Relevance']

export function gatesFromPipeline(pipeline = [], relevanceStatus = 'not_reported', relevanceReason = 'Not reported by this endpoint.') {
  const sourceNames = {
    Schema: ['Message Validation'],
    Certificate: ['Certificate Verification', 'Identity Check'],
    Signature: ['Signature Verification'],
    Freshness: ['Timestamp Check'],
    Replay: ['Replay Check', 'Sequence Check'],
  }
  const gates = RADAR_GATE_NAMES.slice(0, 5).map((name) => {
    const steps = pipeline.filter((step) => sourceNames[name].includes(step.name))
    const failed = steps.find((step) => step.status === 'failed')
    if (failed) return { name, status: 'failed', reason: failed.detail || 'Rejected at this stage.' }
    if (steps.some((step) => step.status === 'success')) return { name, status: 'passed', reason: steps.filter((step) => step.status === 'success').map((step) => step.detail).filter(Boolean).join('; ') }
    if (steps.some((step) => step.status === 'skipped')) return { name, status: 'skipped', reason: 'Not run after an earlier rejection.' }
    return { name, status: 'not_reported', reason: 'This endpoint did not report this gate.' }
  })
  gates.push({ name: 'Relevance', status: relevanceStatus, reason: relevanceReason })
  return gates
}

export function countRadarRecipients(recipients = []) {
  const candidates = recipients.filter((item) => item.delivery_status !== 'sender_excluded')
  return {
    candidates: candidates.length,
    eligible: candidates.filter((item) => ['eligible', 'delivered', 'dropped'].includes(item.delivery_status)).length,
    delivered: candidates.filter((item) => item.delivery_status === 'delivered').length,
    dropped: candidates.filter((item) => item.delivery_status === 'dropped').length,
    invalid: candidates.filter((item) => ['invalid_schema', 'invalid_certificate', 'invalid_signature', 'stale', 'replayed', 'rejected'].includes(item.verification_status)).length,
    verified: candidates.filter((item) => item.accepted).length,
    warnings: candidates.filter((item) => item.safety?.warning).length,
  }
}

export function localRadarPosition(vehicle, sender, rangeMeters, size = 420) {
  const center = size / 2
  const radius = center - 34
  if (!vehicle?.position || !sender?.position) return { x: center, y: center, distance_m: null, in_range: false }
  const latitudeScale = 111320
  const longitudeScale = latitudeScale * Math.cos(sender.position.latitude * Math.PI / 180)
  const east = (vehicle.position.longitude - sender.position.longitude) * longitudeScale
  const north = (vehicle.position.latitude - sender.position.latitude) * latitudeScale
  const distance = Math.hypot(east, north)
  const scaleRange = Math.max(Number(rangeMeters) || 1, 1)
  const cap = radius * 1.12
  const scale = Math.min(radius / scaleRange, cap / Math.max(distance, 0.0001))
  return { x: center + east * scale, y: center - north * scale, distance_m: distance, in_range: distance <= scaleRange }
}

export function radarCountsText(counts) {
  return `${counts.candidates} candidates, ${counts.eligible} in range, ${counts.delivered} delivered, ${counts.verified} verified, ${counts.invalid} rejected, ${counts.warnings} warnings`
}
