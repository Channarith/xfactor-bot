import { useState } from 'react'

interface Strategy {
  name: string
  enabled: boolean
  weight: number
}

export function StrategyPanel() {
  const [strategies, setStrategies] = useState<Strategy[]>([
    { name: 'Technical', enabled: true, weight: 60 },
    { name: 'Momentum', enabled: true, weight: 50 },
    { name: 'MeanReversion', enabled: true, weight: 40 },
    { name: 'NewsSentiment', enabled: true, weight: 40 },
  ])

  const toggleStrategy = (index: number) => {
    const updated = [...strategies]
    updated[index].enabled = !updated[index].enabled
    setStrategies(updated)
  }

  const updateWeight = (index: number, weight: number) => {
    const updated = [...strategies]
    updated[index].weight = weight
    setStrategies(updated)
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h2 className="mb-4 text-lg font-semibold">Strategies</h2>
      <div className="space-y-4">
        {strategies.map((strategy, index) => (
          <div key={strategy.name} className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => toggleStrategy(index)}
                className={`h-5 w-10 rounded-full transition-colors ${
                  strategy.enabled ? 'bg-primary' : 'bg-muted'
                }`}
              >
                <div
                  className={`h-4 w-4 rounded-full bg-white transition-transform ${
                    strategy.enabled ? 'translate-x-5' : 'translate-x-0.5'
                  }`}
                />
              </button>
              <span className={strategy.enabled ? 'text-foreground' : 'text-muted-foreground'}>
                {strategy.name}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min="0"
                max="100"
                value={strategy.weight}
                onChange={(e) => updateWeight(index, parseInt(e.target.value))}
                className="w-20 accent-primary"
                disabled={!strategy.enabled}
              />
              <span className="w-10 text-right text-sm text-muted-foreground">
                {strategy.weight}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

