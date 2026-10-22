import type {
  ArchitectureResponse,
  AttackResponse,
  BroadcastResponse,
  CertificatesResponse,
  CertificateInfo,
  PerformanceData,
  SecurityEvent,
  SendMessageRequest,
  SendMessageResponse,
  StatusSummary,
  SimulationConfig,
  Vehicle,
} from '../types'
import { resolveApiBase } from './apiBase.mjs'

/** Development always uses the Vite proxy; production may set an origin or an /api URL. */
const BASE = resolveApiBase(import.meta.env.DEV, import.meta.env.VITE_API_URL)

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method ?? 'GET'
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch (e) {
    if (e instanceof TypeError) {
      throw new Error(`Unable to reach ${method} ${BASE}${path}. Check that the backend is running and CORS is configured.`)
    }
    throw e
  }
  if (!res.ok) {
    const responseText = await res.text()
    let message = responseText
    try {
      const payload = JSON.parse(responseText) as { detail?: unknown; message?: unknown }
      if (typeof payload.detail === 'string') message = payload.detail
      else if (typeof payload.message === 'string') message = payload.message
    } catch {
      // Keep the raw body when a server returns a non-JSON error.
    }
    throw new Error(`${method} ${BASE}${path}: ${message || `Request failed: ${res.status}`}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  getStatus: () => request<StatusSummary>('/status'),
  getVehicles: () => request<Vehicle[]>('/vehicles'),
  getCertificates: () => request<CertificatesResponse>('/certificates'),
  getCertificateDetail: (id: string) =>
    request<CertificateInfo>(`/certificates/${id}`),
  sendMessage: (body: SendMessageRequest) =>
    request<SendMessageResponse>('/message/send', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  broadcastMessage: (body: { sender_id: string; event: string; speed?: number; latitude?: number; longitude?: number; range_m?: number; packet_loss_probability?: number }) =>
    request<BroadcastResponse>('/message/broadcast', { method: 'POST', body: JSON.stringify(body) }),
  getSimulationConfig: () => request<SimulationConfig>('/simulation/config'),
  updateSimulationConfig: (body: Partial<SimulationConfig>) =>
    request<SimulationConfig>('/simulation/config', { method: 'PUT', body: JSON.stringify(body) }),
  updateVehicle: (id: string, body: { speed?: number; latitude?: number; longitude?: number; direction?: string; acceleration?: number; status?: 'ONLINE' | 'OFFLINE' }) =>
    request<Vehicle>(`/vehicles/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  createVehicle: (body: { vehicle_id: string; speed: number; latitude: number; longitude: number; direction: string }) =>
    request<Vehicle>('/vehicles', { method: 'POST', body: JSON.stringify(body) }),
  advanceSimulation: (seconds = 1) =>
    request<Vehicle[]>(`/simulation/step`, { method: 'POST', body: JSON.stringify({ seconds }) }),
  attackReplay: (receiver_id = 'B001') =>
    request<AttackResponse>('/attack/replay', {
      method: 'POST',
      body: JSON.stringify({ receiver_id }),
    }),
  attackTampering: (field = 'speed', new_value = 180, receiver_id = 'B001') =>
    request<AttackResponse>('/attack/tampering', {
      method: 'POST',
      body: JSON.stringify({ field, new_value, receiver_id }),
    }),
  attackImpersonation: (target_id = 'A001', receiver_id = 'B001') =>
    request<AttackResponse>('/attack/impersonation', {
      method: 'POST',
      body: JSON.stringify({ target_id, receiver_id }),
    }),
  attackFakeCertificate: (receiver_id = 'B001') =>
    request<AttackResponse>('/attack/fake-certificate', {
      method: 'POST',
      body: JSON.stringify({ receiver_id }),
    }),
  attackStale: (receiver_id = 'B001') =>
    request<AttackResponse>('/attack/stale', { method: 'POST', body: JSON.stringify({ receiver_id }) }),
  attackFalseData: (receiver_id = 'B001') =>
    request<AttackResponse>('/attack/false-data', { method: 'POST', body: JSON.stringify({ receiver_id }) }),
  getEvents: (params?: {
    severity?: string
    vehicle_id?: string
    search?: string
  }) => {
    const q = new URLSearchParams()
    if (params?.severity) q.set('severity', params.severity)
    if (params?.vehicle_id) q.set('vehicle_id', params.vehicle_id)
    if (params?.search) q.set('search', params.search)
    const qs = q.toString()
    return request<SecurityEvent[]>(`/events${qs ? `?${qs}` : ''}`)
  },
  clearEvents: () =>
    request<{ cleared: boolean }>('/events', { method: 'DELETE' }),
  getPerformance: () => request<PerformanceData>('/performance'),
  runPerformance: (iterations = 100) =>
    request<PerformanceData>(`/performance/run?iterations=${iterations}`, {
      method: 'POST',
    }),
  getArchitecture: () => request<ArchitectureResponse>('/architecture'),
}
