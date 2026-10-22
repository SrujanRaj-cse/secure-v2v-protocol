export interface RadarGate {
  name: 'Schema' | 'Certificate' | 'Signature' | 'Freshness' | 'Replay' | 'Relevance'
  status: 'passed' | 'failed' | 'skipped' | 'not_reported' | 'warning' | 'relevant' | 'not_relevant'
  reason: string
}
export interface RadarRecipientLike {
  delivery_status: string
  verification_status?: string
  accepted?: boolean
  safety?: { warning?: boolean } | null
}
export declare const RADAR_GATE_NAMES: string[]
export declare function gatesFromPipeline(pipeline?: Array<{ name: string; status: string; detail?: string }>, relevanceStatus?: RadarGate['status'], relevanceReason?: string): RadarGate[]
export declare function countRadarRecipients(recipients?: RadarRecipientLike[]): { candidates: number; eligible: number; delivered: number; dropped: number; invalid: number; verified: number; warnings: number }
export declare function localRadarPosition(vehicle: { position: { latitude: number; longitude: number } } | undefined, sender: { position: { latitude: number; longitude: number } } | undefined, rangeMeters: number, size?: number): { x: number; y: number; distance_m: number | null; in_range: boolean }
export declare function radarCountsText(counts: ReturnType<typeof countRadarRecipients>): string
