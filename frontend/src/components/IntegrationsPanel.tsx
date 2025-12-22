import { useState, useEffect } from 'react'
import { X, Check, AlertCircle, ExternalLink, Eye, EyeOff, Loader2 } from 'lucide-react'
import { getApiBaseUrl } from '../config/api'

interface ConfigModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}

function ConfigModal({ isOpen, onClose, title, children }: ConfigModalProps) {
  if (!isOpen) return null
  
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50" onClick={onClose}>
      <div 
        className="bg-slate-900 border border-slate-700 rounded-lg p-6 max-w-md w-full mx-4 max-h-[80vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

interface AIProvider {
  id: string
  name: string
  description: string
  configured: boolean
  model: string
  status: string
  priority?: number
  recommended?: boolean
  is_fallback?: boolean
  host?: string
  version?: string
  available_models?: string[]
}

export function IntegrationsPanel() {
  const [showConfig, setShowConfig] = useState(false)
  const [configModal, setConfigModal] = useState<string | null>(null)
  const [showPassword, setShowPassword] = useState<Record<string, boolean>>({})
  const [testing, setTesting] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{status: string, message: string} | null>(null)
  const [aiProviders, setAiProviders] = useState<AIProvider[]>([])
  const [currentProvider, setCurrentProvider] = useState<string>('anthropic')
  
  // Form states
  const [anthropicKey, setAnthropicKey] = useState('')
  const [anthropicModel, setAnthropicModel] = useState('claude-sonnet-4-20250514')
  const [openaiKey, setOpenaiKey] = useState('')
  const [openaiModel, setOpenaiModel] = useState('gpt-4-turbo-preview')
  const [ollamaHost, setOllamaHost] = useState('http://localhost:11434')
  const [ollamaModel, setOllamaModel] = useState('llama3.2')
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [plaidClientId, setPlaidClientId] = useState('')
  const [plaidSecret, setPlaidSecret] = useState('')
  const [plaidEnv, setPlaidEnv] = useState('sandbox')
  
  // Broker form states
  const [alpacaApiKey, setAlpacaApiKey] = useState('')
  const [alpacaSecretKey, setAlpacaSecretKey] = useState('')
  const [alpacaPaper, setAlpacaPaper] = useState(true)
  const [polygonApiKey, setPolygonApiKey] = useState('')
  const [tradingviewSecret, setTradingviewSecret] = useState('')
  
  const brokers = [
    { name: 'Interactive Brokers', status: 'connected', color: 'text-profit', configurable: true, id: 'ibkr' },
    { name: 'Alpaca', status: 'ready', color: 'text-muted-foreground', configurable: true, id: 'alpaca' },
    { name: 'Charles Schwab', status: 'ready', color: 'text-muted-foreground', configurable: true, id: 'schwab' },
    { name: 'Tradier', status: 'ready', color: 'text-muted-foreground', configurable: true, id: 'tradier' },
  ]
  
  const dataSources = [
    { name: 'TradingView', status: 'webhooks active', color: 'text-profit', configurable: true, id: 'tradingview' },
    { name: 'Polygon.io', status: 'ready', color: 'text-muted-foreground', configurable: true, id: 'polygon' },
    { name: 'Yahoo Finance', status: 'enabled', color: 'text-profit', configurable: false, id: 'yahoo' },
  ]
  
  const banking = [
    { name: 'Plaid', status: 'ready', color: 'text-muted-foreground', configurable: true, id: 'plaid' },
  ]
  
  // Fetch AI providers on mount
  useEffect(() => {
    fetchAIProviders()
  }, [])
  
  const fetchAIProviders = async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/integrations/ai/providers`)
      if (response.ok) {
        const data = await response.json()
        setAiProviders(data.providers || [])
        setCurrentProvider(data.current_provider || 'anthropic')
        
        // Check for available Ollama models
        const ollama = data.providers?.find((p: AIProvider) => p.id === 'ollama')
        if (ollama?.available_models) {
          setOllamaModels(ollama.available_models)
        }
      }
    } catch (e) {
      console.error('Failed to fetch AI providers:', e)
    }
  }
  
  const testProvider = async (provider: string) => {
    setTesting(provider)
    setTestResult(null)
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/integrations/ai/providers/${provider}/test`, {
        method: 'POST'
      })
      const data = await response.json()
      setTestResult(data)
      
      if (provider === 'ollama' && data.available_models) {
        setOllamaModels(data.available_models)
      }
    } catch (e) {
      setTestResult({ status: 'error', message: 'Connection failed' })
    } finally {
      setTesting(null)
    }
  }
  
  const saveConfiguration = async (type: string, config: Record<string, unknown>) => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/integrations/configure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, config })
      })
      if (response.ok) {
        setConfigModal(null)
        fetchAIProviders() // Refresh status
        return true
      }
    } catch (e) {
      console.error('Failed to save configuration:', e)
    }
    return false
  }
  
  const togglePasswordVisibility = (field: string) => {
    setShowPassword(prev => ({ ...prev, [field]: !prev[field] }))
  }

  const renderAIProviderStatus = (provider: AIProvider) => {
    const statusColor = provider.status === 'ready' || provider.status === 'available'
      ? 'text-green-400'
      : provider.status === 'not_configured'
        ? 'text-yellow-500'
        : 'text-slate-500'
    
    return (
      <div className="flex items-center gap-2">
        <span className={statusColor}>
          {provider.status === 'ready' ? 'configured' : 
           provider.status === 'available' ? 'running' : 
           provider.status}
        </span>
        {provider.recommended && (
          <span className="text-[10px] bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded">recommended</span>
        )}
        {provider.is_fallback && (
          <span className="text-[10px] bg-purple-500/20 text-purple-400 px-1.5 py-0.5 rounded">fallback</span>
        )}
        {currentProvider === provider.id && (
          <span className="text-[10px] bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded">active</span>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Brokers */}
      <div>
        <h4 className="text-sm font-medium text-muted-foreground mb-2">Brokers</h4>
        <div className="space-y-2">
          {brokers.map((broker) => (
            <div key={broker.name} className="flex items-center justify-between text-sm">
              <span className="text-foreground">{broker.name}</span>
              <div className="flex items-center gap-2">
                <span className={broker.color}>{broker.status}</span>
                {showConfig && broker.configurable && (
                  <button 
                    onClick={() => setConfigModal(broker.id)}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    Configure
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* Data Sources */}
      <div>
        <h4 className="text-sm font-medium text-muted-foreground mb-2">Data Sources</h4>
        <div className="space-y-2">
          {dataSources.map((source) => (
            <div key={source.name} className="flex items-center justify-between text-sm">
              <span className="text-foreground">{source.name}</span>
              <div className="flex items-center gap-2">
                <span className={source.color}>{source.status}</span>
                {showConfig && source.configurable && (
                  <button 
                    onClick={() => setConfigModal(source.id)}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    Configure
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* AI Providers - always shown when managing */}
      {showConfig && (
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-2">AI Providers</h4>
          <div className="space-y-2">
            {aiProviders.map((provider) => (
              <div key={provider.id} className="flex items-center justify-between text-sm">
                <span className="text-foreground">{provider.name}</span>
                <div className="flex items-center gap-2">
                  {renderAIProviderStatus(provider)}
                  <button 
                    onClick={() => setConfigModal(provider.id)}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    Configure
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Banking */}
      <div>
        <h4 className="text-sm font-medium text-muted-foreground mb-2">Banking</h4>
        <div className="space-y-2">
          {banking.map((bank) => (
            <div key={bank.name} className="flex items-center justify-between text-sm">
              <span className="text-foreground">{bank.name}</span>
              <div className="flex items-center gap-2">
                <span className={bank.color}>{bank.status}</span>
                {showConfig && bank.configurable && (
                  <button 
                    onClick={() => setConfigModal(bank.id)}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    Configure
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      
      <button 
        onClick={() => setShowConfig(!showConfig)}
        className={`w-full mt-2 px-4 py-2 text-sm rounded-lg transition-colors border ${
          showConfig 
            ? 'bg-blue-600 hover:bg-blue-700 text-white border-blue-500' 
            : 'bg-secondary hover:bg-secondary/80 border-border'
        }`}
      >
        {showConfig ? '✓ Done Managing' : '⚙️ Manage Integrations'}
      </button>
      
      {/* Anthropic Claude Configuration Modal */}
      <ConfigModal
        isOpen={configModal === 'anthropic'}
        onClose={() => { setConfigModal(null); setTestResult(null) }}
        title="Configure Anthropic Claude"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            Claude is the recommended AI provider for trading analysis. Get your API key from{' '}
            <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 inline-flex items-center gap-1">
              Anthropic Console <ExternalLink className="h-3 w-3" />
            </a>
          </p>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">API Key</label>
            <div className="relative">
              <input
                type={showPassword['anthropic'] ? 'text' : 'password'}
                value={anthropicKey}
                onChange={e => setAnthropicKey(e.target.value)}
                placeholder="sk-ant-..."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 pr-10"
              />
              <button
                onClick={() => togglePasswordVisibility('anthropic')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                {showPassword['anthropic'] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Model</label>
            <select
              value={anthropicModel}
              onChange={e => setAnthropicModel(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
            >
              <option value="claude-sonnet-4-20250514">Claude Sonnet 4 (Recommended)</option>
              <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
              <option value="claude-3-opus-20240229">Claude 3 Opus</option>
              <option value="claude-3-haiku-20240307">Claude 3 Haiku (Fast)</option>
            </select>
          </div>
          
          {testResult && (
            <div className={`p-3 rounded-lg text-sm flex items-center gap-2 ${
              testResult.status === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
            }`}>
              {testResult.status === 'success' ? <Check className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
              {testResult.message}
            </div>
          )}
          
          <div className="flex gap-2">
            <button
              onClick={() => testProvider('anthropic')}
              disabled={testing === 'anthropic' || !anthropicKey}
              className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {testing === 'anthropic' ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Test Connection
            </button>
            <button
              onClick={() => saveConfiguration('anthropic', { api_key: anthropicKey, model: anthropicModel })}
              disabled={!anthropicKey}
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm disabled:opacity-50"
            >
              Save
            </button>
          </div>
        </div>
      </ConfigModal>
      
      {/* OpenAI Configuration Modal */}
      <ConfigModal
        isOpen={configModal === 'openai'}
        onClose={() => { setConfigModal(null); setTestResult(null) }}
        title="Configure OpenAI GPT"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            Get your API key from{' '}
            <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 inline-flex items-center gap-1">
              OpenAI Platform <ExternalLink className="h-3 w-3" />
            </a>
          </p>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">API Key</label>
            <div className="relative">
              <input
                type={showPassword['openai'] ? 'text' : 'password'}
                value={openaiKey}
                onChange={e => setOpenaiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 pr-10"
              />
              <button
                onClick={() => togglePasswordVisibility('openai')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                {showPassword['openai'] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Model</label>
            <select
              value={openaiModel}
              onChange={e => setOpenaiModel(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
            >
              <option value="gpt-4-turbo-preview">GPT-4 Turbo (Recommended)</option>
              <option value="gpt-4">GPT-4</option>
              <option value="gpt-4o">GPT-4o</option>
              <option value="gpt-4o-mini">GPT-4o Mini (Fast)</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Budget)</option>
            </select>
          </div>
          
          {testResult && (
            <div className={`p-3 rounded-lg text-sm flex items-center gap-2 ${
              testResult.status === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
            }`}>
              {testResult.status === 'success' ? <Check className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
              {testResult.message}
            </div>
          )}
          
          <div className="flex gap-2">
            <button
              onClick={() => testProvider('openai')}
              disabled={testing === 'openai' || !openaiKey}
              className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {testing === 'openai' ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Test Connection
            </button>
            <button
              onClick={() => saveConfiguration('openai', { api_key: openaiKey, model: openaiModel })}
              disabled={!openaiKey}
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm disabled:opacity-50"
            >
              Save
            </button>
          </div>
        </div>
      </ConfigModal>
      
      {/* Ollama Configuration Modal */}
      <ConfigModal
        isOpen={configModal === 'ollama'}
        onClose={() => { setConfigModal(null); setTestResult(null) }}
        title="Configure Ollama (Local AI)"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            Ollama runs AI models locally on your machine. No API key needed.{' '}
            <a href="https://ollama.com/" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 inline-flex items-center gap-1">
              Download Ollama <ExternalLink className="h-3 w-3" />
            </a>
          </p>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Host URL</label>
            <input
              type="text"
              value={ollamaHost}
              onChange={e => setOllamaHost(e.target.value)}
              placeholder="http://localhost:11434"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Model</label>
            {ollamaModels.length > 0 ? (
              <select
                value={ollamaModel}
                onChange={e => setOllamaModel(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              >
                {ollamaModels.map(model => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={ollamaModel}
                onChange={e => setOllamaModel(e.target.value)}
                placeholder="llama3.2"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500"
              />
            )}
            <p className="text-xs text-slate-500 mt-1">
              Run: <code className="bg-slate-800 px-1 rounded">ollama pull llama3.2</code>
            </p>
          </div>
          
          {testResult && (
            <div className={`p-3 rounded-lg text-sm ${
              testResult.status === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
            }`}>
              <div className="flex items-center gap-2">
                {testResult.status === 'success' ? <Check className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                {testResult.message}
              </div>
              {testResult.status === 'success' && ollamaModels.length > 0 && (
                <p className="text-xs mt-2">Available models: {ollamaModels.join(', ')}</p>
              )}
            </div>
          )}
          
          <div className="flex gap-2">
            <button
              onClick={() => testProvider('ollama')}
              disabled={testing === 'ollama'}
              className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {testing === 'ollama' ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Test Connection
            </button>
            <button
              onClick={() => saveConfiguration('ollama', { host: ollamaHost, model: ollamaModel })}
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm"
            >
              Save
            </button>
          </div>
        </div>
      </ConfigModal>
      
      {/* Plaid Banking Configuration Modal */}
      <ConfigModal
        isOpen={configModal === 'plaid'}
        onClose={() => { setConfigModal(null); setTestResult(null) }}
        title="Configure Plaid Banking"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            Connect your bank accounts via Plaid.{' '}
            <a href="https://dashboard.plaid.com/developers/keys" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 inline-flex items-center gap-1">
              Get API Keys <ExternalLink className="h-3 w-3" />
            </a>
          </p>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Client ID</label>
            <input
              type="text"
              value={plaidClientId}
              onChange={e => setPlaidClientId(e.target.value)}
              placeholder="Plaid Client ID"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Secret Key</label>
            <div className="relative">
              <input
                type={showPassword['plaid'] ? 'text' : 'password'}
                value={plaidSecret}
                onChange={e => setPlaidSecret(e.target.value)}
                placeholder="Plaid Secret"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 pr-10"
              />
              <button
                onClick={() => togglePasswordVisibility('plaid')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                {showPassword['plaid'] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Environment</label>
            <select
              value={plaidEnv}
              onChange={e => setPlaidEnv(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
            >
              <option value="sandbox">Sandbox (Testing)</option>
              <option value="development">Development</option>
              <option value="production">Production</option>
            </select>
          </div>
          
          <button
            onClick={() => saveConfiguration('plaid', { 
              client_id: plaidClientId, 
              secret: plaidSecret, 
              environment: plaidEnv 
            })}
            disabled={!plaidClientId || !plaidSecret}
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm disabled:opacity-50"
          >
            Save Configuration
          </button>
        </div>
      </ConfigModal>
      
      {/* Alpaca Configuration Modal */}
      <ConfigModal
        isOpen={configModal === 'alpaca'}
        onClose={() => { setConfigModal(null); setTestResult(null) }}
        title="Configure Alpaca"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            Commission-free stock trading API.{' '}
            <a href="https://app.alpaca.markets/brokerage/dashboard/overview" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 inline-flex items-center gap-1">
              Get API Keys <ExternalLink className="h-3 w-3" />
            </a>
          </p>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">API Key</label>
            <input
              type="text"
              value={alpacaApiKey}
              onChange={e => setAlpacaApiKey(e.target.value)}
              placeholder="APCA-API-KEY-ID"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Secret Key</label>
            <div className="relative">
              <input
                type={showPassword['alpaca'] ? 'text' : 'password'}
                value={alpacaSecretKey}
                onChange={e => setAlpacaSecretKey(e.target.value)}
                placeholder="Secret Key"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 pr-10"
              />
              <button
                onClick={() => togglePasswordVisibility('alpaca')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                {showPassword['alpaca'] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="alpacaPaper"
              checked={alpacaPaper}
              onChange={e => setAlpacaPaper(e.target.checked)}
              className="rounded border-slate-600 bg-slate-800"
            />
            <label htmlFor="alpacaPaper" className="text-sm text-slate-300">Paper Trading Mode</label>
          </div>
          
          <button
            onClick={() => saveConfiguration('alpaca', { 
              api_key: alpacaApiKey, 
              secret_key: alpacaSecretKey, 
              paper: alpacaPaper 
            })}
            disabled={!alpacaApiKey || !alpacaSecretKey}
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm disabled:opacity-50"
          >
            Save Configuration
          </button>
        </div>
      </ConfigModal>
      
      {/* Polygon.io Configuration Modal */}
      <ConfigModal
        isOpen={configModal === 'polygon'}
        onClose={() => { setConfigModal(null); setTestResult(null) }}
        title="Configure Polygon.io"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            Real-time & historical market data.{' '}
            <a href="https://polygon.io/dashboard/api-keys" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 inline-flex items-center gap-1">
              Get API Key <ExternalLink className="h-3 w-3" />
            </a>
          </p>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">API Key</label>
            <div className="relative">
              <input
                type={showPassword['polygon'] ? 'text' : 'password'}
                value={polygonApiKey}
                onChange={e => setPolygonApiKey(e.target.value)}
                placeholder="Your Polygon API Key"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 pr-10"
              />
              <button
                onClick={() => togglePasswordVisibility('polygon')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                {showPassword['polygon'] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          
          <button
            onClick={() => saveConfiguration('polygon', { api_key: polygonApiKey })}
            disabled={!polygonApiKey}
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm disabled:opacity-50"
          >
            Save Configuration
          </button>
        </div>
      </ConfigModal>
      
      {/* TradingView Configuration Modal */}
      <ConfigModal
        isOpen={configModal === 'tradingview'}
        onClose={() => { setConfigModal(null); setTestResult(null) }}
        title="Configure TradingView Webhooks"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            Set up webhook alerts from TradingView to trigger automated trades.
          </p>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Webhook Secret</label>
            <div className="relative">
              <input
                type={showPassword['tradingview'] ? 'text' : 'password'}
                value={tradingviewSecret}
                onChange={e => setTradingviewSecret(e.target.value)}
                placeholder="Your webhook secret"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 pr-10"
              />
              <button
                onClick={() => togglePasswordVisibility('tradingview')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                {showPassword['tradingview'] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          
          <div className="p-3 bg-slate-800 rounded-lg">
            <p className="text-xs text-slate-400 mb-1">Webhook URL:</p>
            <code className="text-xs text-green-400 break-all">
              {window.location.origin}/api/webhooks/tradingview
            </code>
          </div>
          
          <button
            onClick={() => saveConfiguration('tradingview', { secret: tradingviewSecret })}
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm"
          >
            Save Configuration
          </button>
        </div>
      </ConfigModal>
      
      {/* IBKR Configuration Modal */}
      <ConfigModal
        isOpen={configModal === 'ibkr'}
        onClose={() => { setConfigModal(null); setTestResult(null) }}
        title="Configure Interactive Brokers"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            Connect to TWS or IB Gateway. Make sure TWS/Gateway is running with API enabled.
          </p>
          
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            <p className="text-xs text-amber-400">
              <strong>Note:</strong> IBKR connection requires TWS or IB Gateway running locally. Configure host/port in your .env file.
            </p>
          </div>
          
          <div className="space-y-2 text-sm text-slate-300">
            <p><strong>Default Settings:</strong></p>
            <ul className="list-disc list-inside space-y-1 text-slate-400">
              <li>Host: 127.0.0.1</li>
              <li>Port: 7497 (TWS Paper) / 4002 (Gateway Paper)</li>
              <li>Client ID: 1</li>
            </ul>
          </div>
          
          <a 
            href="https://www.interactivebrokers.com/en/trading/tws.php"
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm text-center"
          >
            Download TWS
          </a>
        </div>
      </ConfigModal>
      
      {/* Schwab Configuration Modal */}
      <ConfigModal
        isOpen={configModal === 'schwab'}
        onClose={() => { setConfigModal(null); setTestResult(null) }}
        title="Configure Charles Schwab"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            Connect to Charles Schwab API.{' '}
            <a href="https://developer.schwab.com/" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 inline-flex items-center gap-1">
              Developer Portal <ExternalLink className="h-3 w-3" />
            </a>
          </p>
          
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            <p className="text-xs text-amber-400">
              Schwab API requires OAuth authentication. Configuration managed via .env file.
            </p>
          </div>
        </div>
      </ConfigModal>
      
      {/* Tradier Configuration Modal */}
      <ConfigModal
        isOpen={configModal === 'tradier'}
        onClose={() => { setConfigModal(null); setTestResult(null) }}
        title="Configure Tradier"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            Low-cost options trading.{' '}
            <a href="https://developer.tradier.com/" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 inline-flex items-center gap-1">
              Developer Portal <ExternalLink className="h-3 w-3" />
            </a>
          </p>
          
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            <p className="text-xs text-amber-400">
              Tradier API configuration managed via .env file.
            </p>
          </div>
        </div>
      </ConfigModal>
    </div>
  )
}
