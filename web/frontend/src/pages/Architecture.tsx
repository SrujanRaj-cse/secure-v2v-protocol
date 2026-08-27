import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { ArchitectureComponent } from '../types'
import { LoadingState, ErrorState } from '../components/MetricCard'

export function ArchitecturePage() {
  const [components, setComponents] = useState<ArchitectureComponent[]>([])
  const [selected, setSelected] = useState<ArchitectureComponent | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getArchitecture()
      .then((d) => setComponents(d.components))
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <ErrorState message={error} />
  if (!components.length) return <LoadingState />

  const byId = Object.fromEntries(components.map((c) => [c.id, c]))

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white">
          Security Architecture
        </h2>
        <p className="text-sm text-slate-500">
          Click any component to learn how it contributes to V2V security
        </p>
      </div>

      <div className="rounded-xl border border-cyber-border bg-cyber-panel p-8">
        <div className="mx-auto max-w-md space-y-2 text-center">
          <ArchNode
            comp={byId.ca}
            onClick={() => setSelected(byId.ca)}
            highlight={selected?.id === 'ca'}
          />
          <FlowArrow />
          <ArchNode
            comp={byId.certificates}
            onClick={() => setSelected(byId.certificates)}
            highlight={selected?.id === 'certificates'}
          />
          <div className="flex justify-center gap-8 py-2">
            <ArchNode
              comp={byId.vehicle_a}
              onClick={() => setSelected(byId.vehicle_a)}
              highlight={selected?.id === 'vehicle_a'}
              small
            />
            <ArchNode
              comp={byId.vehicle_b}
              onClick={() => setSelected(byId.vehicle_b)}
              highlight={selected?.id === 'vehicle_b'}
              small
            />
          </div>
          <FlowArrow label="ECDSA Sign ↔ Verify" />
          <ArchNode
            comp={byId.v2v}
            onClick={() => setSelected(byId.v2v)}
            highlight={selected?.id === 'v2v'}
          />
          <FlowArrow />
          <div className="grid grid-cols-3 gap-2">
            {['cert_verify', 'sig_verify', 'replay'].map((id) => (
              <ArchNode
                key={id}
                comp={byId[id]}
                onClick={() => setSelected(byId[id])}
                highlight={selected?.id === id}
                small
              />
            ))}
          </div>
          <FlowArrow />
          <ArchNode
            comp={byId.result}
            onClick={() => setSelected(byId.result)}
            highlight={selected?.id === 'result'}
          />
        </div>
      </div>

      {selected && (
        <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-5">
          <h3 className="font-semibold text-white">{selected.label}</h3>
          <p className="mt-2 text-sm text-slate-300">{selected.description}</p>
        </div>
      )}
    </div>
  )
}

function ArchNode({
  comp,
  onClick,
  highlight,
  small,
}: {
  comp: ArchitectureComponent
  onClick: () => void
  highlight: boolean
  small?: boolean
}) {
  if (!comp) return null
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg border px-4 py-2 transition ${
        small ? 'text-xs' : 'text-sm'
      } ${
        highlight
          ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-300'
          : 'border-cyber-border bg-cyber-bg text-slate-300 hover:border-cyan-500/30'
      }`}
    >
      {comp.label}
    </button>
  )
}

function FlowArrow({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center text-slate-600">
      <div className="h-4 w-px bg-slate-700" />
      {label && (
        <span className="text-[10px] uppercase tracking-wider">{label}</span>
      )}
      <span className="text-xs">↓</span>
    </div>
  )
}
