import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface PortfolioCardProps {
  title: string
  value: string
  subtitle: string
  trend: 'up' | 'down' | 'neutral'
}

export function PortfolioCard({ title, value, subtitle, trend }: PortfolioCardProps) {
  const trendColors = {
    up: 'text-profit',
    down: 'text-loss',
    neutral: 'text-muted-foreground',
  }
  
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-sm text-muted-foreground">{title}</p>
      <p className={`mt-1 text-2xl font-bold ${trendColors[trend]}`}>{value}</p>
      <div className="mt-1 flex items-center gap-1">
        <TrendIcon className={`h-4 w-4 ${trendColors[trend]}`} />
        <span className={`text-sm ${trendColors[trend]}`}>{subtitle}</span>
      </div>
    </div>
  )
}

