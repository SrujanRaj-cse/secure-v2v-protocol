import type { BroadcastRecipient, PipelineStep, VerificationGate } from './index'

export type RadarLayer = 'all' | 'radio' | 'crypto' | 'safety'
export type RadarPacket = { message: Record<string, unknown>; signature_b64: string; certificate_pem: string }

export interface RadarRecipient extends Omit<BroadcastRecipient, 'safety' | 'verification_gates' | 'verification_ms' | 'processing_ms'> {
  safety: SafetyResult | null
  verification_gates: VerificationGate[]
  verification_ms: number | null
  processing_ms: number | null
}

export interface RadarAttackOverlay {
  receiverId: string
  accepted: boolean
  reason: string
  pipeline: PipelineStep[]
  safety?: SafetyResult
  kind: string
}

export interface RadarCounts {
  candidates: number
  eligible: number
  delivered: number
  dropped: number
  invalid: number
  verified: number
  warnings: number
}

export interface RadarVehiclePosition {
  x: number
  y: number
  distance_m: number | null
  in_range: boolean
}

export interface SafetyResult {
  relevant: boolean
  distance_m: number | null
  relative_speed_mps: number | null
  ttc_seconds: number | null
  reason: string
  warning: boolean
}
