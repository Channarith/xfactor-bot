import { useState } from 'react'
import { 
  Settings, CheckCircle, XCircle, RefreshCw, Eye, EyeOff,
  Building2, Wallet, TrendingUp, Clock, ExternalLink, AlertTriangle,
  DollarSign, CreditCard
} from 'lucide-react'
import { useTradingMode } from '../context/TradingModeContext'

interface BrokerFormData {
  host: string
  port: string
  clientId: string
  accountId: string
  usePaper: boolean
  // IBKR trading permissions
  enableOptions: boolean
  enableFutures: boolean
  enableForex: boolean
  enableCrypto: boolean
  // Options settings
  optionsLevel: number  // 1-4 for IBKR
  optionsBuyingPower: string
  // Futures settings
  futuresMarginType: 'intraday' | 'overnight'
  futuresContracts: string[]
}

export function BrokerConfig() {
  const { broker, connectBroker, disconnectBroker, refreshBrokerData } = useTradingMode()
  const [showConfig, setShowConfig] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [selectedBroker, setSelectedBroker] = useState<string>('ibkr')
  
  const [formData, setFormData] = useState<BrokerFormData>({
    host: '127.0.0.1',
    port: '7497',
    clientId: '1',
    accountId: '',
    usePaper: true,
    enableOptions: false,
    enableFutures: false,
    enableForex: false,
    enableCrypto: false,
    optionsLevel: 2,
    optionsBuyingPower: '',
    futuresMarginType: 'overnight',
    futuresContracts: [],
  })
  
  const [showAdvanced, setShowAdvanced] = useState(false)

  const brokers = [
    { 
      id: 'ibkr', 
      name: 'Interactive Brokers', 
      logo: '🏦',
      description: 'Professional trading platform with global market access',
      features: ['Stocks', 'Options', 'Futures', 'Crypto', 'Forex'],
      minDeposit: '$0 (Paper) / $100 (Live)',
      paperInfo: '$1,000,000 simulated cash for paper trading',
    },
    { 
      id: 'alpaca', 
      name: 'Alpaca', 
      logo: '🦙',
      description: 'Commission-free trading API for stocks and crypto',
      features: ['Stocks', 'Crypto', 'Paper Trading'],
      minDeposit: '$0 (Paper) / $1 (Live)',
      paperInfo: '$100,000 simulated cash for paper trading',
    },
    { 
      id: 'schwab', 
      name: 'Charles Schwab', 
      logo: '💼',
      description: 'Full-service brokerage with Thinkorswim platform',
      features: ['Stocks', 'Options', 'Futures', 'ETFs'],
      minDeposit: '$0',
      comingSoon: true,
    },
    { 
      id: 'tradier', 
      name: 'Tradier', 
      logo: '📊',
      description: 'API-first brokerage for active traders',
      features: ['Stocks', 'Options', 'ETFs'],
      minDeposit: '$0',
      comingSoon: true,
    },
  ]
  
  // Auto-update port based on paper trading toggle
  const handlePaperToggle = (usePaper: boolean) => {
    setFormData({ 
      ...formData, 
      usePaper,
      port: usePaper ? '7497' : '7496'  // IBKR: 7497=paper, 7496=live
    })
  }

  const handleConnect = async () => {
    setConnecting(true)
    setError('')
    
    try {
      const success = await connectBroker(selectedBroker, {
        host: formData.host,
        port: parseInt(formData.port),
        client_id: parseInt(formData.clientId),
        account_id: formData.accountId,
        paper_trading: formData.usePaper,
      })
      
      if (success) {
        setShowConfig(false)
      } else {
        setError('Failed to connect. Check your settings and ensure TWS/Gateway is running.')
      }
    } catch (e) {
      setError('Connection error. Is the broker platform running?')
    }
    
    setConnecting(false)
  }

  const handleDisconnect = () => {
    if (confirm('Are you sure you want to disconnect from the broker?')) {
      disconnectBroker()
    }
  }

  return (
    <div className="space-y-4">
      {/* Connection Status */}
      <div className={`p-4 rounded-lg border ${
        broker.isConnected 
          ? 'bg-profit/10 border-profit/30' 
          : 'bg-secondary/50 border-border'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {broker.isConnected ? (
              <CheckCircle className="h-6 w-6 text-profit" />
            ) : (
              <XCircle className="h-6 w-6 text-muted-foreground" />
            )}
            <div>
              <div className="font-medium">
                {broker.isConnected 
                  ? `Connected to ${broker.provider?.toUpperCase()}` 
                  : 'No Broker Connected'}
              </div>
              <div className="text-sm text-muted-foreground">
                {broker.isConnected 
                  ? `Account: ${broker.accountId} (${broker.accountType})`
                  : 'Connect a broker to enable live trading'}
              </div>
            </div>
          </div>
          
          <div className="flex gap-2">
            {broker.isConnected && (
              <button
                onClick={refreshBrokerData}
                className="p-2 rounded-lg bg-secondary hover:bg-secondary/80"
                title="Refresh"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            )}
            <button
              onClick={broker.isConnected ? handleDisconnect : () => setShowConfig(true)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                broker.isConnected 
                  ? 'bg-loss/20 text-loss hover:bg-loss/30'
                  : 'bg-xfactor-teal text-white hover:bg-xfactor-teal/90'
              }`}
            >
              {broker.isConnected ? 'Disconnect' : 'Connect Broker'}
            </button>
          </div>
        </div>
        
        {/* Account Details */}
        {broker.isConnected && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-border/50">
            <div>
              <div className="text-xs text-muted-foreground flex items-center gap-1">
                <Wallet className="h-3 w-3" />
                Portfolio Value
              </div>
              <div className="text-lg font-bold">
                ${broker.portfolioValue?.toLocaleString() || '0'}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground flex items-center gap-1">
                <DollarSign className="h-3 w-3" />
                Buying Power
              </div>
              <div className="text-lg font-bold">
                ${broker.buyingPower?.toLocaleString() || '0'}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground flex items-center gap-1">
                <Building2 className="h-3 w-3" />
                Account Type
              </div>
              <div className="text-lg font-bold capitalize">
                {broker.accountType || 'Unknown'}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Last Sync
              </div>
              <div className="text-sm font-medium">
                {broker.lastSync 
                  ? new Date(broker.lastSync).toLocaleTimeString() 
                  : 'Never'}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Broker Selection & Config Modal */}
      {showConfig && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-card rounded-xl border border-border max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between p-5 border-b border-border">
              <div className="flex items-center gap-3">
                <Settings className="h-6 w-6 text-xfactor-teal" />
                <div>
                  <h2 className="text-lg font-bold">Connect Broker</h2>
                  <p className="text-sm text-muted-foreground">Select and configure your brokerage</p>
                </div>
              </div>
              <button
                onClick={() => setShowConfig(false)}
                className="p-2 rounded hover:bg-secondary"
              >
                ✕
              </button>
            </div>
            
            {/* Broker Selection */}
            <div className="p-5 border-b border-border">
              <h3 className="text-sm font-medium mb-3">Select Broker</h3>
              <div className="grid grid-cols-2 gap-3">
                {brokers.map((b) => (
                  <button
                    key={b.id}
                    onClick={() => !b.comingSoon && setSelectedBroker(b.id)}
                    disabled={b.comingSoon}
                    className={`p-4 rounded-lg border text-left transition-all ${
                      selectedBroker === b.id 
                        ? 'border-xfactor-teal bg-xfactor-teal/10' 
                        : 'border-border hover:border-xfactor-teal/50'
                    } ${b.comingSoon ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-2xl">{b.logo}</span>
                      <span className="font-medium">{b.name}</span>
                      {b.comingSoon && (
                        <span className="text-xs px-2 py-0.5 rounded bg-secondary text-muted-foreground">
                          Coming Soon
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mb-2">{b.description}</p>
                    <div className="flex flex-wrap gap-1">
                      {b.features.map((f) => (
                        <span key={f} className="text-[10px] px-1.5 py-0.5 rounded bg-secondary">
                          {f}
                        </span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </div>
            
            {/* Configuration Form */}
            {selectedBroker === 'ibkr' && (
              <div className="p-5 space-y-4">
                <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                  <h4 className="font-medium text-blue-400 mb-2">IBKR Setup Instructions</h4>
                  <ol className="text-sm text-muted-foreground space-y-1 list-decimal list-inside">
                    <li>Download and install <a href="https://www.interactivebrokers.com/en/trading/tws.php" target="_blank" className="text-blue-400 hover:underline">Trader Workstation (TWS)</a> or IB Gateway</li>
                    <li>In TWS: Edit → Global Configuration → API → Settings</li>
                    <li>Enable "Enable ActiveX and Socket Clients"</li>
                    <li>Set Socket port to 7497 (paper) or 7496 (live)</li>
                    <li>Disable "Read-Only API" to allow trading</li>
                  </ol>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-muted-foreground">Host</label>
                    <input
                      type="text"
                      value={formData.host}
                      onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                      className="w-full mt-1 px-3 py-2 rounded-lg bg-secondary border border-border"
                      placeholder="127.0.0.1"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Port</label>
                    <input
                      type="text"
                      value={formData.port}
                      onChange={(e) => setFormData({ ...formData, port: e.target.value })}
                      className="w-full mt-1 px-3 py-2 rounded-lg bg-secondary border border-border"
                      placeholder="7497"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      7497 = Paper, 7496 = Live
                    </p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Client ID</label>
                    <input
                      type="text"
                      value={formData.clientId}
                      onChange={(e) => setFormData({ ...formData, clientId: e.target.value })}
                      className="w-full mt-1 px-3 py-2 rounded-lg bg-secondary border border-border"
                      placeholder="1"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Account ID (optional)</label>
                    <input
                      type="text"
                      value={formData.accountId}
                      onChange={(e) => setFormData({ ...formData, accountId: e.target.value })}
                      className="w-full mt-1 px-3 py-2 rounded-lg bg-secondary border border-border"
                      placeholder="DU1234567"
                    />
                  </div>
                </div>
                
                <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/50">
                  <input
                    type="checkbox"
                    id="usePaper"
                    checked={formData.usePaper}
                    onChange={(e) => handlePaperToggle(e.target.checked)}
                    className="w-4 h-4 rounded"
                  />
                  <label htmlFor="usePaper" className="flex-1">
                    <div className="font-medium">Paper Trading Mode</div>
                    <div className="text-xs text-muted-foreground">
                      Use simulated trading (recommended for testing)
                    </div>
                  </label>
                </div>
                
                {formData.usePaper && (
                  <div className="p-3 rounded-lg bg-profit/10 border border-profit/20 flex items-start gap-2">
                    <DollarSign className="h-5 w-5 text-profit shrink-0 mt-0.5" />
                    <div className="text-sm">
                      <p className="font-medium text-profit">Paper Trading Account</p>
                      <p className="text-muted-foreground mt-1">
                        {selectedBroker === 'ibkr' 
                          ? <>IBKR provides <strong>$1,000,000</strong> in simulated cash. Port 7497 is used for paper trading.</>
                          : <>Alpaca provides <strong>$100,000</strong> in simulated cash for paper trading.</>
                        }
                      </p>
                    </div>
                  </div>
                )}
                
                {!formData.usePaper && (
                  <div className="p-3 rounded-lg bg-loss/10 border border-loss/20 flex items-start gap-2">
                    <AlertTriangle className="h-5 w-5 text-loss shrink-0 mt-0.5" />
                    <div className="text-sm">
                      <strong className="text-loss">Warning:</strong> Live trading uses real money. 
                      Ensure you understand the risks before proceeding.
                    </div>
                  </div>
                )}
                
                {/* Advanced Trading Settings */}
                <div className="border-t border-border pt-4 mt-4">
                  <button
                    type="button"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="flex items-center justify-between w-full text-left"
                  >
                    <span className="font-medium">Advanced Trading Settings</span>
                    <span className={`transition-transform ${showAdvanced ? 'rotate-180' : ''}`}>▼</span>
                  </button>
                  
                  {showAdvanced && (
                    <div className="mt-4 space-y-4">
                      {/* Trading Permissions */}
                      <div className="p-4 rounded-lg bg-secondary/50">
                        <h4 className="font-medium mb-3">Trading Permissions</h4>
                        <div className="grid grid-cols-2 gap-3">
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={formData.enableOptions}
                              onChange={(e) => setFormData({...formData, enableOptions: e.target.checked})}
                              className="w-4 h-4 rounded"
                            />
                            <span className="text-sm">Options Trading</span>
                          </label>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={formData.enableFutures}
                              onChange={(e) => setFormData({...formData, enableFutures: e.target.checked})}
                              className="w-4 h-4 rounded"
                            />
                            <span className="text-sm">Futures Trading</span>
                          </label>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={formData.enableForex}
                              onChange={(e) => setFormData({...formData, enableForex: e.target.checked})}
                              className="w-4 h-4 rounded"
                            />
                            <span className="text-sm">Forex Trading</span>
                          </label>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={formData.enableCrypto}
                              onChange={(e) => setFormData({...formData, enableCrypto: e.target.checked})}
                              className="w-4 h-4 rounded"
                            />
                            <span className="text-sm">Crypto Trading</span>
                          </label>
                        </div>
                      </div>
                      
                      {/* Options Configuration */}
                      {formData.enableOptions && (
                        <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                          <h4 className="font-medium text-blue-400 mb-3">📊 Options Configuration</h4>
                          <div className="space-y-3">
                            <div>
                              <label className="text-sm text-muted-foreground">Options Level (IBKR)</label>
                              <select
                                value={formData.optionsLevel}
                                onChange={(e) => setFormData({...formData, optionsLevel: parseInt(e.target.value)})}
                                className="w-full mt-1 px-3 py-2 rounded-lg bg-secondary border border-border"
                              >
                                <option value={1}>Level 1 - Covered Calls/Puts</option>
                                <option value={2}>Level 2 - Long Calls/Puts, Spreads</option>
                                <option value={3}>Level 3 - Naked Puts, Straddles</option>
                                <option value={4}>Level 4 - Naked Calls, Full Permissions</option>
                              </select>
                            </div>
                            <div className="text-xs text-muted-foreground">
                              <p className="font-medium mb-1">Level Permissions:</p>
                              <ul className="space-y-0.5">
                                <li>• Level 1: Buy-writes, covered calls</li>
                                <li>• Level 2: Long options, spreads, iron condors</li>
                                <li>• Level 3: Naked puts, cash-secured puts</li>
                                <li>• Level 4: Full naked options permissions</li>
                              </ul>
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {/* Futures Configuration */}
                      {formData.enableFutures && (
                        <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20">
                          <h4 className="font-medium text-amber-400 mb-3">📈 Futures Configuration</h4>
                          <div className="space-y-3">
                            <div>
                              <label className="text-sm text-muted-foreground">Margin Type</label>
                              <select
                                value={formData.futuresMarginType}
                                onChange={(e) => setFormData({...formData, futuresMarginType: e.target.value as 'intraday' | 'overnight'})}
                                className="w-full mt-1 px-3 py-2 rounded-lg bg-secondary border border-border"
                              >
                                <option value="intraday">Intraday (50% margin)</option>
                                <option value="overnight">Overnight (Full margin)</option>
                              </select>
                            </div>
                            <div>
                              <label className="text-sm text-muted-foreground">Enabled Contracts</label>
                              <div className="grid grid-cols-3 gap-2 mt-2">
                                {['ES', 'NQ', 'RTY', 'YM', 'CL', 'GC', 'SI', 'ZB', 'ZN'].map(contract => (
                                  <label key={contract} className="flex items-center gap-2 text-sm cursor-pointer">
                                    <input
                                      type="checkbox"
                                      checked={formData.futuresContracts.includes(contract)}
                                      onChange={(e) => {
                                        const contracts = e.target.checked
                                          ? [...formData.futuresContracts, contract]
                                          : formData.futuresContracts.filter(c => c !== contract)
                                        setFormData({...formData, futuresContracts: contracts})
                                      }}
                                      className="w-3 h-3 rounded"
                                    />
                                    <span>{contract}</span>
                                  </label>
                                ))}
                              </div>
                            </div>
                            <div className="text-xs text-muted-foreground">
                              <p className="font-medium mb-1">Contract Descriptions:</p>
                              <ul className="grid grid-cols-2 gap-1">
                                <li>• ES: E-mini S&P 500</li>
                                <li>• NQ: E-mini Nasdaq 100</li>
                                <li>• RTY: E-mini Russell 2000</li>
                                <li>• YM: E-mini Dow Jones</li>
                                <li>• CL: Crude Oil</li>
                                <li>• GC: Gold</li>
                                <li>• SI: Silver</li>
                                <li>• ZB: 30-Year T-Bonds</li>
                                <li>• ZN: 10-Year T-Notes</li>
                              </ul>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {selectedBroker === 'alpaca' && (
              <div className="p-5 space-y-4">
                <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                  <h4 className="font-medium text-blue-400 mb-2">Alpaca Setup</h4>
                  <ol className="text-sm text-muted-foreground space-y-1 list-decimal list-inside">
                    <li>Create an account at <a href="https://alpaca.markets" target="_blank" className="text-blue-400 hover:underline">alpaca.markets</a></li>
                    <li>Go to your dashboard and generate API keys</li>
                    <li>Enter your API Key and Secret below</li>
                  </ol>
                </div>
                
                <div className="grid grid-cols-1 gap-4">
                  <div>
                    <label className="text-sm text-muted-foreground">API Key</label>
                    <input
                      type="text"
                      className="w-full mt-1 px-3 py-2 rounded-lg bg-secondary border border-border font-mono"
                      placeholder="PKXXXXXXXXXXXXXXXX"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">API Secret</label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        className="w-full mt-1 px-3 py-2 pr-10 rounded-lg bg-secondary border border-border font-mono"
                        placeholder="••••••••••••••••"
                      />
                      <button
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {error && (
              <div className="mx-5 p-3 rounded-lg bg-loss/10 border border-loss/20 text-loss text-sm">
                {error}
              </div>
            )}
            
            {/* Footer */}
            <div className="flex gap-3 p-5 border-t border-border">
              <button
                onClick={() => setShowConfig(false)}
                className="flex-1 px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleConnect}
                disabled={connecting}
                className="flex-1 px-4 py-2 rounded-lg bg-xfactor-teal text-white font-medium hover:bg-xfactor-teal/90 text-sm disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {connecting ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  <>
                    <CheckCircle className="h-4 w-4" />
                    Connect
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Funding Information */}
      {broker.isConnected && (
        <div className="p-4 rounded-lg border border-border bg-secondary/30">
          <div className="flex items-center gap-2 mb-3">
            <CreditCard className="h-5 w-5 text-xfactor-teal" />
            <h3 className="font-medium">Fund Your Account</h3>
          </div>
          <p className="text-sm text-muted-foreground mb-3">
            To trade with real money, you need to deposit funds directly through your broker's platform.
          </p>
          <a
            href={
              broker.provider === 'ibkr' 
                ? 'https://www.interactivebrokers.com/sso/Login' 
                : broker.provider === 'alpaca'
                  ? 'https://app.alpaca.markets/brokerage/banking/transfers'
                  : '#'
            }
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-xfactor-teal text-white text-sm font-medium hover:bg-xfactor-teal/90"
          >
            <ExternalLink className="h-4 w-4" />
            Open {broker.provider?.toUpperCase()} Funding Portal
          </a>
        </div>
      )}
    </div>
  )
}

