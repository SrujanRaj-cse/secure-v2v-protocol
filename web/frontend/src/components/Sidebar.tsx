import { NavLink } from 'react-router-dom'
import {
  Activity,
  Building2,
  FileText,
  Gauge,
  LayoutDashboard,
  Network,
  Radio,
  ShieldAlert,
} from 'lucide-react'

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/communication', label: 'V2V Communication', icon: Radio },
  { to: '/certificates', label: 'Certificate Authority', icon: Building2 },
  { to: '/attacks', label: 'Attack Simulation', icon: ShieldAlert },
  { to: '/events', label: 'Security Event Log', icon: FileText },
  { to: '/performance', label: 'Performance', icon: Gauge },
  { to: '/architecture', label: 'Architecture', icon: Network },
]

export function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-cyber-border bg-cyber-panel p-4">
      <nav className="flex flex-col gap-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                isActive
                  ? 'bg-cyan-500/10 text-cyber-accent ring-1 ring-cyan-500/30'
                  : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-8 rounded-lg border border-cyber-border bg-cyber-bg p-3">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Activity className="h-3 w-3 text-cyber-success" />
          System Online
        </div>
      </div>
    </aside>
  )
}
