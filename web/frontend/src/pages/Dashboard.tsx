import { useCallback, useEffect, useState } from 'react'
import {
  Car,
  CheckCircle,
  Shield,
  ShieldAlert,
  Send,
  XCircle,
} from 'lucide-react'
import { api } from '../services/api'
import type { StatusSummary, Vehicle } from '../types'
import { MetricCard } from '../components/MetricCard'
import { VehicleCard } from '../components/VehicleCard'
import { VehicleNetwork } from '../components/VehicleNetwork'
import { LoadingState, ErrorState } from '../components/MetricCard'

export function DashboardPage() {
  const [status, setStatus] = useState<StatusSummary | null>(null)
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [s, v] = await Promise.all([api.getStatus(), api.getVehicles()])
      setStatus(s)
      setVehicles(v)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Backend unavailable')
    }
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 2000)
    return () => clearInterval(id)
  }, [load])

  if (error && !status) return <ErrorState message={error} onRetry={load} />
  if (!status) return <LoadingState message="Connecting to V2V backend..." />

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white">Security Dashboard</h2>
        <p className="text-sm text-slate-500">
          Live monitoring of secure vehicle-to-vehicle communication
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <MetricCard
          label="Active Vehicles"
          value={status.active_vehicles}
          icon={<Car className="h-4 w-4" />}
        />
        <MetricCard
          label="Messages Sent"
          value={status.messages_sent}
          icon={<Send className="h-4 w-4" />}
        />
        <MetricCard
          label="Verified"
          value={status.messages_verified}
          icon={<CheckCircle className="h-4 w-4" />}
          accent="green"
        />
        <MetricCard
          label="Rejected"
          value={status.messages_rejected}
          icon={<XCircle className="h-4 w-4" />}
          accent="red"
        />
        <MetricCard
          label="Attacks Detected"
          value={status.attacks_detected}
          icon={<ShieldAlert className="h-4 w-4" />}
          accent="amber"
        />
        <MetricCard
          label="CA Status"
          value={status.ca_status}
          icon={<Shield className="h-4 w-4" />}
          accent="green"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <VehicleNetwork vehicles={vehicles} />
        <div className="space-y-4">
          <h3 className="text-sm font-medium uppercase tracking-wider text-slate-500">
            Vehicle Status
          </h3>
          {vehicles.map((v) => (
            <VehicleCard key={v.vehicle_id} vehicle={v} />
          ))}
        </div>
      </div>
    </div>
  )
}
