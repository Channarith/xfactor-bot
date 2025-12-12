import { AlertTriangle } from 'lucide-react'

export function RiskControls() {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h2 className="mb-4 text-lg font-semibold">Risk Controls</h2>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Max Position</span>
          <input
            type="text"
            defaultValue="$50,000"
            className="w-24 rounded bg-input px-2 py-1 text-right text-sm"
          />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Daily Loss Limit</span>
          <input
            type="text"
            defaultValue="-3%"
            className="w-24 rounded bg-input px-2 py-1 text-right text-sm"
          />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Max Drawdown</span>
          <input
            type="text"
            defaultValue="-10%"
            className="w-24 rounded bg-input px-2 py-1 text-right text-sm"
          />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">VIX Halt</span>
          <input
            type="text"
            defaultValue="35"
            className="w-24 rounded bg-input px-2 py-1 text-right text-sm"
          />
        </div>
      </div>
      
      <div className="mt-4 rounded-lg bg-destructive/10 p-3">
        <div className="flex items-center gap-2 text-destructive">
          <AlertTriangle className="h-4 w-4" />
          <span className="text-sm font-medium">Kill Switch Ready</span>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          Will cancel all orders and optionally close positions
        </p>
      </div>
    </div>
  )
}

