export interface StatusSummary {
  active_vehicles: number
  messages_sent: number
  messages_verified: number
  messages_rejected: number
  attacks_detected: number
  ca_status: string
  ca_name: string
  certificate_count: number
}

export interface Vehicle {
  vehicle_id: string
  speed: number
  position: { latitude: number; longitude: number }
  direction: string
  sequence_number: number
  certificate_status: string
  connection_status: string
  security_status: string
  last_event: string | null
  status?: 'ONLINE' | 'OFFLINE'
  heading_degrees?: number | null
  acceleration?: number
}

export interface CertificateInfo {
  vehicle_id: string
  status: string
  issuer: string
  subject: string
  serial_number: string
  not_valid_before: string
  not_valid_after: string
  algorithm: string
  public_key_abbrev: string
  signature_valid: boolean
  verification?: { valid: boolean; reason: string }
}

export interface CertificatesResponse {
  ca: {
    name: string
    status: string
    algorithm: string
    certificate_count: number
    issuer: string
    not_valid_before: string
    not_valid_after: string
    public_key_abbrev: string
  }
  vehicles: CertificateInfo[]
}

export interface PipelineStep {
  name: string
  status: 'pending' | 'processing' | 'success' | 'failed' | 'warning' | 'skipped'
  detail: string
}

export interface SendMessageRequest {
  sender_id: string
  receiver_id: string
  event: string
  speed?: number
  latitude?: number
  longitude?: number
}

export interface SendMessageResponse {
  accepted: boolean
  reason: string
  pipeline: PipelineStep[]
  message_hash: string
  packet: { message: Record<string, unknown>; signature_b64: string; certificate_pem: string }
}

export interface VerificationGate {
  name: 'Schema' | 'Certificate' | 'Signature' | 'Freshness' | 'Replay' | 'Relevance'
  status: 'passed' | 'failed' | 'skipped' | 'not_reported' | 'warning' | 'relevant' | 'not_relevant'
  reason: string | null
}

export interface BroadcastRecipient {
  receiver_id: string
  message_id: string
  distance_m: number | null
  delivery_status: string
  attempted_delivery: boolean
  verification_status: string
  safety_status: string
  accepted: boolean
  rejection_reason: string | null
  processing_ms: number
  verification_ms?: number
  safety_evaluation_performed: boolean
  safety: { relevant: boolean; distance_m: number | null; relative_speed_mps: number | null; ttc_seconds: number | null; reason: string; warning: boolean } | null
  verification_gates?: VerificationGate[]
}

export interface BroadcastResponse {
  message_id: string
  packet: { message: Record<string, unknown>; signature_b64: string; certificate_pem: string }
  message_hash: string
  signature_count: number
  range_m: number
  packet_loss_probability: number
  seed: number
  recipients: BroadcastRecipient[]
}

export interface SimulationConfig {
  communication_range_m: number
  packet_loss_probability: number
  random_seed: number
  relevance_threshold_m: number
}

export interface AttackResponse {
  attack: string
  accepted: boolean
  reason: string
  pipeline: PipelineStep[]
  packet?: { message: Record<string, unknown>; signature_b64: string; certificate_pem: string }
  safety?: { relevant: boolean; distance_m: number | null; relative_speed_mps: number | null; ttc_seconds: number | null; reason: string; warning: boolean }
  original_message?: Record<string, unknown>
  modified_message?: Record<string, unknown>
  replayed_message?: Record<string, unknown>
  forged_message?: Record<string, unknown>
  explanation?: string
  cryptographically_authenticated?: boolean
  plausibility_suspicious?: boolean
  plausibility_flags?: string[]
}

export interface SecurityEvent {
  id: string
  timestamp: string
  level: string
  severity: 'info' | 'success' | 'warning' | 'error'
  message: string
  source: string
  vehicle_id: string | null
}

export interface PerformanceData {
  iterations: number
  timestamp_validity_seconds?: number
  avg_message_creation_ms: number
  avg_signing_ms: number
  avg_verification_ms: number
  avg_replay_detection_ms: number
  avg_tamper_detection_ms: number
}

export interface ArchitectureComponent {
  id: string
  label: string
  description: string
}

export interface ArchitectureResponse {
  components: ArchitectureComponent[]
  flow: string[]
}
