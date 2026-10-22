import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { BroadcastResponse, SimulationConfig, Vehicle } from '../src/types'
import { TrustRadarPage } from '../src/pages/TrustRadar'
import { VerificationRails } from '../src/components/trust-radar/VerificationRails'
import type { RadarRecipient } from '../src/types/trustRadar'

vi.mock('../src/services/api', () => ({
  api: {
    getVehicles: vi.fn(),
    getSimulationConfig: vi.fn(),
    updateSimulationConfig: vi.fn(),
    broadcastMessage: vi.fn(),
    sendMessage: vi.fn(),
    updateVehicle: vi.fn(),
    advanceSimulation: vi.fn(),
    attackReplay: vi.fn(),
    attackTampering: vi.fn(),
    attackImpersonation: vi.fn(),
    attackFakeCertificate: vi.fn(),
    attackStale: vi.fn(),
    attackFalseData: vi.fn(),
  },
}))

import { api } from '../src/services/api'

const config: SimulationConfig = { communication_range_m: 500, packet_loss_probability: 0, random_seed: 428, relevance_threshold_m: 500 }
const vehicles: Vehicle[] = [
  { vehicle_id: 'A001', speed: 80, position: { latitude: 17.385, longitude: 78.4867 }, direction: 'North', heading_degrees: 0, sequence_number: 0, certificate_status: 'VALID', connection_status: 'SECURE', security_status: 'SECURE', last_event: null, status: 'ONLINE' },
  { vehicle_id: 'B001', speed: 120, position: { latitude: 17.3841, longitude: 78.4867 }, direction: 'North', heading_degrees: 0, sequence_number: 0, certificate_status: 'VALID', connection_status: 'SECURE', security_status: 'SECURE', last_event: null, status: 'ONLINE' },
]
const message = { vehicle_id: 'A001', message_id: 'msg-1', sequence_number: 1, timestamp: 1_800_000_000, speed: 80, direction: 'North', event: 'EMERGENCY_BRAKING', position: { latitude: 17.385, longitude: 78.4867 } }
const passed = ['Schema', 'Certificate', 'Signature', 'Freshness', 'Replay'].map((name) => ({ name, status: 'passed' as const, reason: 'Passed.' }))
const response = (overrides: Partial<BroadcastResponse> = {}): BroadcastResponse => ({
  message_id: 'msg-1',
  packet: { message, signature_b64: 'signature-data', certificate_pem: '-----BEGIN CERTIFICATE-----\npublic-cert\n-----END CERTIFICATE-----' },
  message_hash: '0123456789abcdef0123456789abcdef', signature_count: 1, range_m: 500, packet_loss_probability: 0, seed: 428,
  recipients: [
    { receiver_id: 'A001', message_id: 'msg-1', distance_m: 0, delivery_status: 'sender_excluded', attempted_delivery: false, verification_status: 'not_attempted', safety_status: 'not_evaluated', accepted: false, rejection_reason: 'Sender is not a recipient', processing_ms: 0, safety_evaluation_performed: false, safety: null },
    { receiver_id: 'B001', message_id: 'msg-1', distance_m: 100, delivery_status: 'delivered', attempted_delivery: true, verification_status: 'accepted', safety_status: 'warning_generated', accepted: true, rejection_reason: null, processing_ms: 1.2, safety_evaluation_performed: true, safety: { relevant: true, distance_m: 100, relative_speed_mps: 11.111, ttc_seconds: 9, reason: 'Vehicle is approaching the event area', warning: true }, verification_gates: [...passed, { name: 'Relevance', status: 'warning', reason: 'Vehicle is approaching the event area' }] },
  ],
  ...overrides,
})

let container: HTMLDivElement
let root: Root

async function renderRadar() {
  await act(async () => { root.render(createElement(TrustRadarPage)); await Promise.resolve() })
}

async function click(button: Element | null) {
  if (!button) throw new Error('Expected button was not found')
  await act(async () => { button.dispatchEvent(new MouseEvent('click', { bubbles: true })); await Promise.resolve() })
}

async function inputValue(input: HTMLInputElement, value: string) {
  await act(async () => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
    setter?.call(input, value)
    input.dispatchEvent(new Event('input', { bubbles: true }))
    input.dispatchEvent(new Event('change', { bubbles: true }))
  })
}

beforeEach(() => {
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
  vi.mocked(api.getVehicles).mockResolvedValue(vehicles)
  vi.mocked(api.getSimulationConfig).mockResolvedValue(config)
  vi.mocked(api.updateSimulationConfig).mockResolvedValue(config)
  vi.mocked(api.broadcastMessage).mockResolvedValue(response())
  vi.mocked(api.updateVehicle).mockImplementation(async (id, update) => ({ ...vehicles.find((vehicle) => vehicle.vehicle_id === id)!, position: { latitude: update.latitude ?? 0, longitude: update.longitude ?? 0 } }))
  vi.mocked(api.advanceSimulation).mockResolvedValue(vehicles)
})

afterEach(async () => {
  await act(async () => { root.unmount() })
  container.remove()
})

describe('Trust Radar page', () => {
  it('loads display values from the API response and updates when the next response changes', async () => {
    vi.mocked(api.broadcastMessage).mockResolvedValueOnce(response()).mockResolvedValueOnce(response({ recipients: [
      response().recipients[0],
      { ...response().recipients[1], delivery_status: 'outside_range', verification_status: 'not_attempted', accepted: false, rejection_reason: '510 m exceeds range', safety: null, safety_evaluation_performed: false, verification_gates: undefined },
    ] }))
    await renderRadar()
    await click([...container.querySelectorAll('button')].find((button) => button.textContent === 'Broadcast') ?? null)
    expect(container.textContent).toContain('warning raised')
    await click([...container.querySelectorAll('button')].find((button) => button.textContent === 'Broadcast') ?? null)
    expect(container.textContent).toContain('510 m exceeds range')
    expect(container.textContent).not.toContain('warning raised')
  })

  it('switches modes and hides the manual receiver selector in broadcast mode', async () => {
    await renderRadar()
    expect(container.textContent).not.toContain('Receiver')
    await click([...container.querySelectorAll('button')].find((button) => button.textContent === 'unicast') ?? null)
    expect(container.textContent).toContain('Receiver')
    await click([...container.querySelectorAll('button')].find((button) => button.textContent === 'broadcast') ?? null)
    expect(container.textContent).not.toContain('Receiver')
  })

  it('prevents duplicate broadcasts while the request is in flight', async () => {
    let finish: ((value: BroadcastResponse) => void) | undefined
    vi.mocked(api.broadcastMessage).mockReturnValueOnce(new Promise((resolve) => { finish = resolve }))
    await renderRadar()
    const button = [...container.querySelectorAll('button')].find((item) => item.textContent === 'Broadcast') ?? null
    await click(button)
    expect(button?.hasAttribute('disabled')).toBe(true)
    await click(button)
    expect(api.broadcastMessage).toHaveBeenCalledTimes(1)
    await act(async () => { finish?.(response()) })
  })

  it('shows backend unavailable errors and empty states', async () => {
    vi.mocked(api.getVehicles).mockRejectedValueOnce(new Error('backend offline'))
    await renderRadar()
    expect(container.textContent).toContain('backend offline')
    await act(async () => { root.unmount() })
    container.replaceChildren()
    root = createRoot(container)
    vi.mocked(api.getVehicles).mockResolvedValueOnce([])
    vi.mocked(api.getSimulationConfig).mockResolvedValueOnce(config)
    await renderRadar()
    expect(container.textContent).toContain('backend returned no vehicles')
  })

  it('validates input before submitting and displays actual range and loss units', async () => {
    await renderRadar()
    const rangeInput = [...container.querySelectorAll('input')].find((input) => input.getAttribute('min') === '0' && input.getAttribute('max') === '100000')
    expect(rangeInput?.getAttribute('aria-invalid')).toBe('false')
    if (rangeInput) await inputValue(rangeInput, '100001')
    expect(rangeInput?.getAttribute('aria-invalid')).toBe('true')
    expect([...container.querySelectorAll('button')].find((button) => button.textContent === 'Broadcast')?.hasAttribute('disabled')).toBe(true)
    expect(container.textContent).toContain('metres')
    expect(container.textContent).toContain('%')
    expect(api.broadcastMessage).not.toHaveBeenCalled()
  })
})

describe('verification rail status rendering', () => {
  it('renders outside, dropped, rejected-gate, verified-relevant and verified-irrelevant rows', async () => {
    const row = (id: string, delivery: string, gates: RadarRecipient['verification_gates'], accepted = false, safety: RadarRecipient['safety'] = null): RadarRecipient => ({
      receiver_id: id, message_id: 'x', distance_m: 20, delivery_status: delivery, attempted_delivery: delivery === 'delivered', verification_status: accepted ? 'accepted' : delivery === 'outside_range' || delivery === 'dropped' ? 'not_attempted' : 'invalid_signature', safety_status: 'not_evaluated', accepted, rejection_reason: accepted ? null : 'actual backend reason', processing_ms: 1, verification_ms: 1, safety_evaluation_performed: Boolean(safety), safety, verification_gates: gates,
    })
    const base = ['Schema', 'Certificate', 'Signature', 'Freshness', 'Replay'].map((name) => ({ name, status: 'passed' as const, reason: 'passed' }))
    const rows = [
      { ...row('V001', 'outside_range', []), rejection_reason: 'outside range' },
      row('V002', 'dropped', []),
      row('V003', 'delivered', base.map((gate, index) => index === 2 ? { ...gate, status: 'failed', reason: 'invalid signature' } : { ...gate, status: index > 2 ? 'skipped' as const : gate.status }), false),
      row('V004', 'delivered', [...base, { name: 'Relevance', status: 'warning', reason: 'TTC 2s' }], true, { relevant: true, distance_m: 20, relative_speed_mps: 2, ttc_seconds: 2, reason: 'approaching', warning: true }),
      row('V005', 'delivered', [...base, { name: 'Relevance', status: 'not_relevant', reason: 'travelling away' }], true, { relevant: false, distance_m: 20, relative_speed_mps: -2, ttc_seconds: null, reason: 'travelling away', warning: false }),
    ]
    await act(async () => { root.render(createElement(VerificationRails, { recipientVehicles: rows.map((item) => ({ vehicle_id: item.receiver_id })), recipients: rows, attack: null, phase: 4 })) })
    expect(container.textContent).toContain('outside range')
    expect(container.textContent).toContain('dropped by channel')
    expect(container.textContent).toContain('invalid_signature: actual backend reason')
    expect(container.textContent).toContain('warning raised')
    expect(container.textContent).toContain('authentic, not relevant')
    expect(container.querySelector('[aria-label="Signature: failed. invalid signature"]')).not.toBeNull()
  })

  it('stops each rejected security rail at the backend-reported gate', async () => {
    const names = ['Schema', 'Certificate', 'Signature', 'Freshness', 'Replay'] as const
    const recipients = names.map((failedName) => {
      const gates = [...names, 'Relevance' as const].map((name) => ({
        name,
        status: name === failedName ? 'failed' as const : names.indexOf(name as typeof failedName) < names.indexOf(failedName) ? 'passed' as const : 'skipped' as const,
        reason: name === failedName ? `rejected at ${name}` : 'stage result',
      }))
      return {
        receiver_id: `V-${failedName}`,
        message_id: 'm',
        distance_m: 20,
        delivery_status: 'delivered',
        attempted_delivery: true,
        verification_status: 'rejected',
        safety_status: 'not_evaluated',
        accepted: false,
        rejection_reason: `rejected at ${failedName}`,
        processing_ms: 1,
        verification_ms: 1,
        safety_evaluation_performed: false,
        safety: null,
        verification_gates: gates,
      } satisfies RadarRecipient
    })
    await act(async () => { root.render(createElement(VerificationRails, { recipientVehicles: recipients.map((item) => ({ vehicle_id: item.receiver_id })), recipients, attack: null, phase: 4 })) })
    for (const gate of names) {
      expect(container.querySelector(`[aria-label="${gate}: failed. rejected at ${gate}"]`)).not.toBeNull()
    }
  })
})
