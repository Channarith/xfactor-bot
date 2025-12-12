import { Activity, AlertTriangle, Pause, Play, Power } from 'lucide-react'

interface HeaderProps {
  connected: boolean
}

export function Header({ connected }: HeaderProps) {
  return (
    <header className="border-b border-border bg-card px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold text-foreground">
            Trading Bot Control Panel
          </h1>
          <span className="rounded-full bg-primary/20 px-3 py-1 text-sm text-primary">
            Paper Mode
          </span>
        </div>
        
        <div className="flex items-center gap-6">
          {/* Connection Status */}
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full ${connected ? 'bg-profit' : 'bg-loss'}`} />
            <span className="text-sm text-muted-foreground">
              {connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          
          {/* Trading Controls */}
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-2 rounded-lg bg-secondary px-4 py-2 text-sm hover:bg-secondary/80">
              <Pause className="h-4 w-4" />
              Pause
            </button>
            <button className="flex items-center gap-2 rounded-lg bg-destructive px-4 py-2 text-sm text-destructive-foreground hover:bg-destructive/80">
              <Power className="h-4 w-4" />
              Kill Switch
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}

