import { useEffect, useState } from 'react'
import { Gauge, RefreshCw } from 'lucide-react'
import { api } from '../services/api'
import type { PerformanceData } from '../types'
import { PerformanceChart } from '../components/PerformanceChart'
import { MetricCard } from '../components/MetricCard'
import { LoadingState, ErrorState } from '../components/MetricCard'

export function PerformancePage() {
  const [data, setData] = useState<PerformanceData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)

  const load = () => {
    api
      .getPerformance()
      .then(setData)
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    load()
  }, [])

  const runBenchmark = async () => {
    setRunning(true)
    setError(null)
    try {
      const res = await api.runPerformance(100)
      setData(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Benchmark failed')
    } finally {
      setRunning(false)
    }
  }

  if (!data && !error) return <LoadingState message="Loading performance data..." />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">
            Performance Analytics
          </h2>
          <p className="text-sm text-slate-500">
            Cryptographic operation benchmarks from the real implementation
          </p>
        </div>
        <button
          type="button"
          onClick={runBenchmark}
          disabled={running}
          className="flex items-center gap-2 rounded-lg border border-cyber-border px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${running ? 'animate-spin' : ''}`} />
          {running ? 'Running...' : 'Run Benchmark'}
        </button>
      </div>

      {error && !data && (
        <ErrorState message={error} onRetry={runBenchmark} />
      )}

      {data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <MetricCard
              label="Message Creation"
              value={`${data.avg_message_creation_ms.toFixed(4)} ms`}
              icon={<Gauge className="h-4 w-4" />}
            />
            <MetricCard
              label="Signing"
              value={`${data.avg_signing_ms.toFixed(4)} ms`}
              icon={<Gauge className="h-4 w-4" />}
              accent="cyan"
            />
            <MetricCard
              label="Verification"
              value={`${data.avg_verification_ms.toFixed(4)} ms`}
              icon={<Gauge className="h-4 w-4" />}
              accent="green"
            />
            <MetricCard
              label="Replay Detection"
              value={`${data.avg_replay_detection_ms.toFixed(4)} ms`}
              icon={<Gauge className="h-4 w-4" />}
              accent="amber"
            />
            <MetricCard
              label="Tamper Detection"
              value={`${data.avg_tamper_detection_ms.toFixed(4)} ms`}
              icon={<Gauge className="h-4 w-4" />}
              accent="red"
            />
          </div>
          <PerformanceChart data={data} />
        </>
      )}
    </div>
  )
}
