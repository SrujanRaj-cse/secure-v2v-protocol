import assert from 'node:assert/strict'
import test from 'node:test'
import { countRadarRecipients, gatesFromPipeline, localRadarPosition, radarCountsText } from '../src/services/trustRadarData.mjs'

test('maps reported unicast stages and leaves relevance not reported', () => {
  const gates = gatesFromPipeline([
    { name: 'Message Validation', status: 'success', detail: 'Structure valid' },
    { name: 'Certificate Verification', status: 'success', detail: 'CA-signed' },
    { name: 'Signature Verification', status: 'failed', detail: 'Invalid digital signature' },
  ])
  assert.deepEqual(gates.map(({ status }) => status), ['passed', 'passed', 'failed', 'not_reported', 'not_reported', 'not_reported'])
  assert.equal(gates[2].reason, 'Invalid digital signature')
})

test('summarizes live recipient values and ignores sender row', () => {
  const counts = countRadarRecipients([
    { delivery_status: 'sender_excluded', accepted: false },
    { delivery_status: 'delivered', verification_status: 'accepted', accepted: true, safety: { warning: true } },
    { delivery_status: 'dropped', verification_status: 'not_attempted', accepted: false },
    { delivery_status: 'outside_range', verification_status: 'not_attempted', accepted: false },
    { delivery_status: 'delivered', verification_status: 'replayed', accepted: false },
  ])
  assert.deepEqual(counts, { candidates: 4, eligible: 3, delivered: 2, dropped: 1, invalid: 1, verified: 1, warnings: 1 })
  assert.match(radarCountsText(counts), /4 candidates, 3 in range/)
})

test('projects backend coordinates relative to sender and communication range', () => {
  const sender = { position: { latitude: 17.385, longitude: 78.4867 } }
  const northbound = { position: { latitude: 17.386, longitude: 78.4867 } }
  const point = localRadarPosition(northbound, sender, 500, 420)
  assert.equal(point.in_range, true)
  assert.ok(point.y < 210)
  const outside = localRadarPosition({ position: { latitude: 17.39, longitude: 78.4867 } }, sender, 500, 420)
  assert.equal(outside.in_range, false)
  assert.ok(Math.hypot(outside.x - 210, outside.y - 210) > Math.hypot(point.x - 210, point.y - 210))
})
