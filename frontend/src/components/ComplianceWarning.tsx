/**
 * Compliance Warning Components
 * 
 * Displays trading compliance warnings and violations to users.
 * Includes modals for PDT warnings, Good Faith violations, etc.
 */

import { useState, useEffect } from 'react'
import { 
  AlertTriangle, 
  Shield, 
  XCircle, 
  AlertCircle,
  Info,
  CheckCircle,
  Clock,
  DollarSign,
  TrendingUp,
  AlertOctagon,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from 'lucide-react'

// Get API base URL
const getApiBaseUrl = (): string => {
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:9876'
    }
    return ''
  }
  return ''
}

// Types
interface ComplianceViolation {
  type: string
  severity: 'info' | 'warning' | 'critical'
  action: string
  title: string
  description: string
  regulation: string
  details: Record<string, unknown>
  timestamp: string
}

interface ComplianceCheckResult {
  allowed: boolean
  action: string
  violations: ComplianceViolation[]
  warnings: string[]
  requires_confirmation: boolean
  stop_trading: boolean
  symbol?: string
  side?: string
  quantity?: number
}

interface ComplianceStatus {
  account_type: string
  equity: number
  pdt_status: {
    is_pattern_day_trader: boolean
    day_trades_last_5_days: number
    remaining_day_trades: number | null
    pdt_threshold: number
    equity_requirement: number
    meets_equity_requirement: boolean
  }
  trading_status: {
    trading_allowed: boolean
    stop_reason: string | null
  }
  restrictions: {
    restricted: boolean
    restriction_type: string | null
    restriction_ends: string | null
  }
  settlement: {
    settlement_days: number
    unsettled_positions: number
  }
  recent_violations: ComplianceViolation[]
}

// Props
interface ComplianceWarningModalProps {
  isOpen: boolean
  onClose: () => void
  checkResult: ComplianceCheckResult
  onConfirm?: () => void
  onCancel?: () => void
}

interface ComplianceStatusBadgeProps {
  onClick?: () => void
}

// Severity to color mapping
const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'critical':
      return 'red'
    case 'warning':
      return 'yellow'
    case 'info':
    default:
      return 'blue'
  }
}

const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case 'critical':
      return <XCircle className="h-5 w-5 text-red-400" />
    case 'warning':
      return <AlertTriangle className="h-5 w-5 text-yellow-400" />
    case 'info':
    default:
      return <Info className="h-5 w-5 text-blue-400" />
  }
}

/**
 * Compliance Warning Modal
 * 
 * Shows when a trade triggers compliance warnings or violations.
 */
export function ComplianceWarningModal({
  isOpen,
  onClose,
  checkResult,
  onConfirm,
  onCancel,
}: ComplianceWarningModalProps) {
  if (!isOpen) return null

  const hasBlockingViolation = checkResult.violations.some(v => v.action === 'block')
  const hasCriticalViolation = checkResult.violations.some(v => v.severity === 'critical')
  
  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
    >
      <div 
        className="bg-slate-900 rounded-xl border border-slate-700 shadow-2xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className={`p-4 border-b ${hasCriticalViolation ? 'border-red-500/50 bg-red-500/10' : 'border-yellow-500/50 bg-yellow-500/10'}`}>
          <div className="flex items-center gap-3">
            {hasCriticalViolation ? (
              <AlertOctagon className="h-6 w-6 text-red-400" />
            ) : (
              <AlertTriangle className="h-6 w-6 text-yellow-400" />
            )}
            <div>
              <h2 className={`text-lg font-semibold ${hasCriticalViolation ? 'text-red-400' : 'text-yellow-400'}`}>
                {hasBlockingViolation ? 'Trade Blocked' : 'Compliance Warning'}
              </h2>
              <p className="text-sm text-slate-400">
                {checkResult.symbol} - {checkResult.side?.toUpperCase()} {checkResult.quantity} shares
              </p>
            </div>
          </div>
        </div>
        
        {/* Violations */}
        <div className="p-4 space-y-4">
          {checkResult.violations.map((violation, index) => (
            <div 
              key={index}
              className={`p-4 rounded-lg border ${
                violation.severity === 'critical' 
                  ? 'bg-red-500/10 border-red-500/30' 
                  : violation.severity === 'warning'
                    ? 'bg-yellow-500/10 border-yellow-500/30'
                    : 'bg-blue-500/10 border-blue-500/30'
              }`}
            >
              <div className="flex items-start gap-3">
                {getSeverityIcon(violation.severity)}
                <div className="flex-1">
                  <h3 className="font-medium text-white">{violation.title}</h3>
                  <p className="text-sm text-slate-300 mt-1">{violation.description}</p>
                  <p className="text-xs text-slate-500 mt-2">
                    Regulation: {violation.regulation}
                  </p>
                  
                  {/* Details */}
                  {Object.keys(violation.details).length > 0 && (
                    <div className="mt-2 p-2 bg-black/20 rounded text-xs">
                      {Object.entries(violation.details).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-slate-500">{key.replace(/_/g, ' ')}:</span>
                          <span className="text-slate-300">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          
          {/* Additional Warnings */}
          {checkResult.warnings.length > 0 && (
            <div className="p-4 bg-blue-500/10 rounded-lg border border-blue-500/30">
              <h4 className="font-medium text-blue-400 mb-2">Additional Warnings</h4>
              <ul className="text-sm text-slate-300 space-y-1">
                {checkResult.warnings.map((warning, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <Info className="h-4 w-4 text-blue-400 mt-0.5 flex-shrink-0" />
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Stop Trading Warning */}
          {checkResult.stop_trading && (
            <div className="p-4 bg-red-500/20 rounded-lg border border-red-500/50">
              <div className="flex items-center gap-2 text-red-400 font-medium">
                <AlertOctagon className="h-5 w-5" />
                Trading Stopped for Today
              </div>
              <p className="text-sm text-slate-300 mt-1">
                Bot trading has been automatically stopped to prevent further violations.
                You can manually resume from the Risk Management panel.
              </p>
            </div>
          )}
        </div>
        
        {/* Actions */}
        <div className="p-4 border-t border-slate-700 flex justify-end gap-3">
          {hasBlockingViolation ? (
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
            >
              Close
            </button>
          ) : (
            <>
              <button
                onClick={() => {
                  onCancel?.()
                  onClose()
                }}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
              >
                Cancel Trade
              </button>
              {checkResult.requires_confirmation && (
                <button
                  onClick={() => {
                    onConfirm?.()
                    onClose()
                  }}
                  className="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 text-white rounded-lg transition-colors flex items-center gap-2"
                >
                  <AlertTriangle className="h-4 w-4" />
                  I Understand, Proceed
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Compliance Status Badge
 * 
 * Shows current PDT status and day trades remaining in the header.
 */
export function ComplianceStatusBadge({ onClick }: ComplianceStatusBadgeProps) {
  const [status, setStatus] = useState<ComplianceStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/compliance/status`)
        if (response.ok) {
          const data = await response.json()
          setStatus(data)
        } else {
          setError('Failed to fetch compliance status')
        }
      } catch (e) {
        // API might not be available yet
        setError('Compliance API not available')
      } finally {
        setLoading(false)
      }
    }
    
    fetchStatus()
    // Refresh every 30 seconds
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [])
  
  if (loading || error || !status) {
    return null
  }
  
  const { pdt_status, trading_status, restrictions } = status
  
  // Don't show badge for paper trading
  if (status.account_type === 'paper') {
    return null
  }
  
  // Determine badge color based on status
  let badgeColor = 'bg-green-500/20 text-green-400 border-green-500/30'
  let icon = <CheckCircle className="h-3 w-3" />
  let text = 'Trading OK'
  
  if (!trading_status.trading_allowed) {
    badgeColor = 'bg-red-500/20 text-red-400 border-red-500/30'
    icon = <XCircle className="h-3 w-3" />
    text = 'Trading Stopped'
  } else if (restrictions.restricted) {
    badgeColor = 'bg-red-500/20 text-red-400 border-red-500/30'
    icon = <Shield className="h-3 w-3" />
    text = 'Restricted'
  } else if (pdt_status.is_pattern_day_trader && !pdt_status.meets_equity_requirement) {
    badgeColor = 'bg-red-500/20 text-red-400 border-red-500/30'
    icon = <AlertTriangle className="h-3 w-3" />
    text = 'PDT Restricted'
  } else if (pdt_status.remaining_day_trades !== null && pdt_status.remaining_day_trades <= 1) {
    badgeColor = 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
    icon = <AlertTriangle className="h-3 w-3" />
    text = `${pdt_status.remaining_day_trades} DT Left`
  } else if (pdt_status.remaining_day_trades !== null && pdt_status.remaining_day_trades <= 2) {
    badgeColor = 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
    icon = <Clock className="h-3 w-3" />
    text = `${pdt_status.remaining_day_trades} DTs Left`
  }
  
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1 px-2 py-1 text-xs rounded-full border ${badgeColor} hover:opacity-80 transition-opacity`}
      title="Click for compliance details"
    >
      {icon}
      <span>{text}</span>
    </button>
  )
}

/**
 * Compliance Status Panel
 * 
 * Full panel showing detailed compliance information.
 */
export function ComplianceStatusPanel() {
  const [status, setStatus] = useState<ComplianceStatus | null>(null)
  const [dayTrades, setDayTrades] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statusRes, tradesRes] = await Promise.all([
          fetch(`${getApiBaseUrl()}/api/compliance/status`),
          fetch(`${getApiBaseUrl()}/api/compliance/day-trades`),
        ])
        
        if (statusRes.ok) {
          setStatus(await statusRes.json())
        }
        if (tradesRes.ok) {
          const data = await tradesRes.json()
          setDayTrades(data.day_trades || [])
        }
      } catch (e) {
        console.error('Failed to fetch compliance data:', e)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
    const interval = setInterval(fetchData, 60000)
    return () => clearInterval(interval)
  }, [])
  
  if (loading) {
    return (
      <div className="p-4 text-center text-slate-400">
        Loading compliance status...
      </div>
    )
  }
  
  if (!status) {
    return (
      <div className="p-4 text-center text-slate-400">
        Compliance data unavailable
      </div>
    )
  }
  
  const { pdt_status, trading_status, restrictions, settlement } = status
  
  return (
    <div className="space-y-4">
      {/* Trading Status */}
      <div className={`p-4 rounded-lg border ${
        trading_status.trading_allowed 
          ? 'bg-green-500/10 border-green-500/30' 
          : 'bg-red-500/10 border-red-500/30'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {trading_status.trading_allowed ? (
              <CheckCircle className="h-5 w-5 text-green-400" />
            ) : (
              <XCircle className="h-5 w-5 text-red-400" />
            )}
            <span className="font-medium text-white">
              {trading_status.trading_allowed ? 'Trading Allowed' : 'Trading Stopped'}
            </span>
          </div>
          {!trading_status.trading_allowed && trading_status.stop_reason && (
            <span className="text-sm text-slate-400">{trading_status.stop_reason}</span>
          )}
        </div>
      </div>
      
      {/* PDT Status */}
      <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium text-white flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-slate-400" />
            Pattern Day Trader Status
          </h3>
          {pdt_status.is_pattern_day_trader ? (
            <span className="px-2 py-0.5 text-xs bg-yellow-500/20 text-yellow-400 rounded-full border border-yellow-500/30">
              PDT Flagged
            </span>
          ) : (
            <span className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded-full border border-green-500/30">
              Not PDT
            </span>
          )}
        </div>
        
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-slate-400">Day Trades (5 days):</span>
            <span className="ml-2 text-white">{pdt_status.day_trades_last_5_days} / {pdt_status.pdt_threshold}</span>
          </div>
          <div>
            <span className="text-slate-400">Remaining:</span>
            <span className={`ml-2 ${
              pdt_status.remaining_day_trades !== null && pdt_status.remaining_day_trades <= 1 
                ? 'text-yellow-400 font-medium' 
                : 'text-white'
            }`}>
              {pdt_status.remaining_day_trades ?? 'Unlimited'}
            </span>
          </div>
          <div>
            <span className="text-slate-400">Account Equity:</span>
            <span className="ml-2 text-white">${status.equity.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-slate-400">PDT Minimum:</span>
            <span className={`ml-2 ${
              pdt_status.meets_equity_requirement ? 'text-green-400' : 'text-red-400'
            }`}>
              ${pdt_status.equity_requirement.toLocaleString()}
              {pdt_status.meets_equity_requirement ? ' ✓' : ' ✗'}
            </span>
          </div>
        </div>
        
        {/* Day Trades List */}
        {dayTrades.length > 0 && (
          <div className="mt-4">
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-sm text-slate-400 hover:text-white transition-colors"
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              Recent Day Trades ({dayTrades.length})
            </button>
            
            {expanded && (
              <div className="mt-2 space-y-2">
                {dayTrades.map((trade, index) => (
                  <div key={index} className="p-2 bg-slate-800 rounded text-xs flex justify-between">
                    <span className="text-white">{trade.symbol}</span>
                    <span className="text-slate-400">{trade.trade_date}</span>
                    <span className={trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                      {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Restrictions */}
      {restrictions.restricted && (
        <div className="p-4 bg-red-500/10 rounded-lg border border-red-500/30">
          <div className="flex items-center gap-2 text-red-400 font-medium mb-2">
            <Shield className="h-5 w-5" />
            Account Restricted
          </div>
          <p className="text-sm text-slate-300">
            Type: {restrictions.restriction_type}
          </p>
          <p className="text-sm text-slate-400">
            Restriction ends: {restrictions.restriction_ends}
          </p>
        </div>
      )}
      
      {/* Settlement Info */}
      <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
        <h3 className="font-medium text-white flex items-center gap-2 mb-2">
          <Clock className="h-4 w-4 text-slate-400" />
          Settlement Status
        </h3>
        <div className="text-sm">
          <span className="text-slate-400">Settlement Period:</span>
          <span className="ml-2 text-white">T+{settlement.settlement_days}</span>
        </div>
        {settlement.unsettled_positions > 0 && (
          <div className="text-sm mt-1">
            <span className="text-yellow-400">
              {settlement.unsettled_positions} unsettled position(s)
            </span>
          </div>
        )}
      </div>
      
      {/* Recent Violations */}
      {status.recent_violations.length > 0 && (
        <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
          <h3 className="font-medium text-white flex items-center gap-2 mb-3">
            <AlertCircle className="h-4 w-4 text-slate-400" />
            Recent Violations
          </h3>
          <div className="space-y-2">
            {status.recent_violations.slice(0, 5).map((violation, index) => (
              <div key={index} className={`p-2 rounded text-sm ${
                violation.severity === 'critical' 
                  ? 'bg-red-500/10' 
                  : violation.severity === 'warning'
                    ? 'bg-yellow-500/10'
                    : 'bg-blue-500/10'
              }`}>
                <div className="flex items-center gap-2">
                  {getSeverityIcon(violation.severity)}
                  <span className="text-white">{violation.title}</span>
                </div>
                <p className="text-xs text-slate-400 mt-1">{violation.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Learn More Link */}
      <div className="text-center">
        <a 
          href="#" 
          onClick={(e) => {
            e.preventDefault()
            // Could open help modal to Compliance section
          }}
          className="text-sm text-blue-400 hover:text-blue-300 flex items-center justify-center gap-1"
        >
          Learn about trading regulations
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  )
}

/**
 * Pre-trade compliance check hook
 */
export function useComplianceCheck() {
  const [checking, setChecking] = useState(false)
  
  const checkOrder = async (
    symbol: string,
    side: 'buy' | 'sell',
    quantity: number,
    estimatedPrice: number,
    isClosing: boolean = false
  ): Promise<ComplianceCheckResult | null> => {
    setChecking(true)
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/compliance/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          side,
          quantity,
          estimated_price: estimatedPrice,
          is_closing: isClosing,
        }),
      })
      
      if (response.ok) {
        return await response.json()
      }
      return null
    } catch (e) {
      console.error('Compliance check failed:', e)
      return null
    } finally {
      setChecking(false)
    }
  }
  
  const recordTrade = async (
    symbol: string,
    side: 'buy' | 'sell',
    quantity: number,
    price: number
  ) => {
    try {
      await fetch(`${getApiBaseUrl()}/api/compliance/record-trade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, side, quantity, price }),
      })
    } catch (e) {
      console.error('Failed to record trade:', e)
    }
  }
  
  const confirmProceed = async (symbol: string, side: string) => {
    try {
      await fetch(`${getApiBaseUrl()}/api/compliance/confirm-proceed?symbol=${symbol}&side=${side}`, {
        method: 'POST',
      })
    } catch (e) {
      console.error('Failed to confirm proceed:', e)
    }
  }
  
  return {
    checking,
    checkOrder,
    recordTrade,
    confirmProceed,
  }
}

export default ComplianceWarningModal

