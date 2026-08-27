import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { SecurityEvent } from '../types'
import { EventLogPanel } from '../components/EventLog'
import { ErrorState } from '../components/MetricCard'

export function EventLogPage() {
  const [events, setEvents] = useState<SecurityEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState({
    severity: 'all',
    vehicle_id: 'all',
    search: '',
  })

  const load = useCallback(async () => {
    try {
      const data = await api.getEvents({
        severity: filters.severity !== 'all' ? filters.severity : undefined,
        vehicle_id: filters.vehicle_id !== 'all' ? filters.vehicle_id : undefined,
        search: filters.search || undefined,
      })
      setEvents(data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load events')
    }
  }, [filters])

  useEffect(() => {
    load()
    const id = setInterval(load, 2000)
    return () => clearInterval(id)
  }, [load])

  const handleClear = async () => {
    await api.clearEvents()
    load()
  }

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white">Security Event Log</h2>
        <p className="text-sm text-slate-500">
          Real-time audit trail from backend security operations
        </p>
      </div>

      {error && <ErrorState message={error} onRetry={load} />}
      <EventLogPanel
        events={events}
        onClear={handleClear}
        filters={filters}
        onFilterChange={handleFilterChange}
      />
    </div>
  )
}
