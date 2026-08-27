import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { PerformanceData } from '../types'

export function PerformanceChart({ data }: { data: PerformanceData }) {
  const chartData = [
    { name: 'Creation', ms: data.avg_message_creation_ms },
    { name: 'Signing', ms: data.avg_signing_ms },
    { name: 'Verification', ms: data.avg_verification_ms },
    { name: 'Replay Det.', ms: data.avg_replay_detection_ms },
    { name: 'Tamper Det.', ms: data.avg_tamper_detection_ms },
  ]

  return (
    <div className="rounded-xl border border-cyber-border bg-cyber-panel p-5">
      <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-slate-500">
        Average Latency (ms) — {data.iterations} iterations
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              background: '#111827',
              border: '1px solid #1e293b',
              borderRadius: 8,
              color: '#e2e8f0',
            }}
            formatter={(v) => [`${Number(v).toFixed(4)} ms`, 'Avg']}
          />
          <Bar dataKey="ms" fill="#06b6d4" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
