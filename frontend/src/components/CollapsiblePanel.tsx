import { useState, ReactNode } from 'react'
import { ChevronDown, ChevronUp, Maximize2, Minimize2 } from 'lucide-react'

interface CollapsiblePanelProps {
  title: string
  children: ReactNode
  defaultExpanded?: boolean
  icon?: ReactNode
  badge?: string | number
  className?: string
  headerClassName?: string
}

export function CollapsiblePanel({
  title,
  children,
  defaultExpanded = true,
  icon,
  badge,
  className = '',
  headerClassName = ''
}: CollapsiblePanelProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const [isMaximized, setIsMaximized] = useState(false)

  const toggleExpand = () => {
    if (!isMaximized) {
      setIsExpanded(!isExpanded)
    }
  }

  const toggleMaximize = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsMaximized(!isMaximized)
    if (!isMaximized) {
      setIsExpanded(true)
    }
  }

  // Maximized view - full screen overlay
  if (isMaximized) {
    return (
      <div 
        className="fixed inset-0 z-50 bg-background/95 backdrop-blur-sm overflow-auto p-6"
        onClick={() => setIsMaximized(false)}
        onKeyDown={(e) => e.key === 'Escape' && setIsMaximized(false)}
      >
        <div 
          className="max-w-7xl mx-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <div className={`rounded-lg border border-border bg-card ${className}`}>
            {/* Header */}
            <div
              className={`flex items-center justify-between px-4 py-3 border-b border-border cursor-pointer hover:bg-secondary/30 transition-colors ${headerClassName}`}
            >
              <div className="flex items-center gap-3">
                {icon && <span className="text-xfactor-teal">{icon}</span>}
                <h2 className="text-lg font-semibold text-foreground">{title}</h2>
                {badge !== undefined && (
                  <span className="px-2 py-0.5 text-xs rounded-full bg-xfactor-money/20 text-xfactor-money border border-xfactor-money/30">
                    {badge}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={toggleMaximize}
                  className="p-1.5 rounded-md hover:bg-secondary transition-colors"
                  title="Exit fullscreen"
                >
                  <Minimize2 className="h-4 w-4 text-muted-foreground" />
                </button>
              </div>
            </div>
            
            {/* Content - Full height */}
            <div className="p-4 min-h-[80vh]">
              {children}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`rounded-lg border border-border bg-card overflow-hidden transition-all duration-200 ${className}`}>
      {/* Header */}
      <div
        onClick={toggleExpand}
        className={`flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-secondary/30 transition-colors select-none ${headerClassName}`}
      >
        <div className="flex items-center gap-3">
          {icon && <span className="text-xfactor-teal">{icon}</span>}
          <h2 className="text-lg font-semibold text-foreground">{title}</h2>
          {badge !== undefined && (
            <span className="px-2 py-0.5 text-xs rounded-full bg-xfactor-money/20 text-xfactor-money border border-xfactor-money/30">
              {badge}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleMaximize}
            className="p-1.5 rounded-md hover:bg-secondary transition-colors"
            title="Maximize"
          >
            <Maximize2 className="h-4 w-4 text-muted-foreground" />
          </button>
          <div className="p-1">
            {isExpanded ? (
              <ChevronUp className="h-5 w-5 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-5 w-5 text-muted-foreground" />
            )}
          </div>
        </div>
      </div>
      
      {/* Content */}
      {isExpanded && (
        <div className="p-4 pt-2 collapsible-content">
          {children}
        </div>
      )}
    </div>
  )
}

