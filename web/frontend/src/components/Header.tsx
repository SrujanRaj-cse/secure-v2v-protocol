import { Shield } from 'lucide-react'

export function Header() {
  return (
    <header className="border-b border-cyber-border bg-cyber-panel/80 backdrop-blur px-6 py-4">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-500/10 ring-1 ring-cyan-500/30">
          <Shield className="h-5 w-5 text-cyber-accent" />
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-wide text-white">
            SECURE V2V PROTOCOL
          </h1>
          <p className="text-xs text-slate-400">
            Real-Time Vehicle Communication Security Monitor
          </p>
        </div>
      </div>
    </header>
  )
}
