import type {
  ArchitectureResponse,
  AttackResponse,
  CertificatesResponse,
  CertificateInfo,
  PerformanceData,
  SecurityEvent,
  SendMessageRequest,
  SendMessageResponse,
  StatusSummary,
  Vehicle,
} from '../types'

/** Local dev: `/api` (Vite proxy). Production: set VITE_API_URL on Render (origin only, no /api). */
const apiOrigin = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '')
const BASE = apiOrigin ? `${apiOrigin}/api` : '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Request failed: ${res.status}`)
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
