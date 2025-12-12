import { useState, useRef, useEffect } from 'react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface ProviderInfo {
  available: boolean
  model?: string
  host?: string
  reason?: string
  models?: string[]
}

interface ProvidersData {
  current_provider: string
  providers: {
    openai: ProviderInfo
    ollama: ProviderInfo
    anthropic: ProviderInfo
  }
}

type LLMProvider = 'openai' | 'ollama' | 'anthropic'

export function AIAssistant() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [insights, setInsights] = useState<string[]>([])
  const [examples, setExamples] = useState<string[]>([])
  const [sessionId] = useState(() => `session-${Date.now()}`)
  const [isExpanded, setIsExpanded] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [providers, setProviders] = useState<ProvidersData | null>(null)
  const [currentProvider, setCurrentProvider] = useState<LLMProvider>('openai')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    // Fetch initial insights, examples, and providers
    fetchInsights()
    fetchExamples()
    fetchProviders()
  }, [])

  const fetchProviders = async () => {
    try {
      const res = await fetch('/api/ai/providers')
      if (res.ok) {
        const data = await res.json()
        setProviders(data)
        setCurrentProvider(data.current_provider || 'openai')
      }
    } catch (err) {
      console.error('Failed to fetch providers:', err)
    }
  }

  const switchProvider = async (provider: LLMProvider) => {
    try {
      const res = await fetch('/api/ai/providers/set', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
      })
      if (res.ok) {
        setCurrentProvider(provider)
        fetchProviders() // Refresh provider info
        // Show confirmation message
        const confirmMsg: Message = {
          id: `msg-${Date.now()}-system`,
          role: 'assistant',
          content: `✅ Switched to ${provider.toUpperCase()} provider${
            provider === 'ollama' ? ' (local LLM)' : ''
          }`,
          timestamp: new Date(),
        }
        setMessages(prev => [...prev, confirmMsg])
      } else {
        const error = await res.json()
        const errorMsg: Message = {
          id: `msg-${Date.now()}-error`,
          role: 'assistant',
          content: `❌ Failed to switch provider: ${error.detail}`,
          timestamp: new Date(),
        }
        setMessages(prev => [...prev, errorMsg])
      }
    } catch (err) {
      console.error('Failed to switch provider:', err)
    }
  }

  const fetchInsights = async () => {
    try {
      const res = await fetch('/api/ai/insights')
      if (res.ok) {
        const data = await res.json()
        setInsights(data.insights || [])
      }
    } catch (err) {
      console.error('Failed to fetch insights:', err)
    }
  }

  const fetchExamples = async () => {
    try {
      const res = await fetch('/api/ai/examples')
      if (res.ok) {
        const data = await res.json()
        setExamples(data.examples || [])
      }
    } catch (err) {
      console.error('Failed to fetch examples:', err)
    }
  }

  const sendMessage = async (query?: string) => {
    const messageText = query || input.trim()
    if (!messageText || isLoading) return

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: messageText,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const res = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: messageText,
          session_id: sessionId,
          include_context: true,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        const assistantMessage: Message = {
          id: `msg-${Date.now()}-assistant`,
          role: 'assistant',
          content: data.response,
          timestamp: new Date(),
        }
        setMessages(prev => [...prev, assistantMessage])
      } else {
        const errorMessage: Message = {
          id: `msg-${Date.now()}-error`,
          role: 'assistant',
          content: 'Sorry, I encountered an error processing your request. Please try again.',
          timestamp: new Date(),
        }
        setMessages(prev => [...prev, errorMessage])
      }
    } catch (err) {
      console.error('Chat error:', err)
      const errorMessage: Message = {
        id: `msg-${Date.now()}-error`,
        role: 'assistant',
        content: 'Unable to connect to the AI assistant. Please check your connection.',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const clearChat = async () => {
    try {
      await fetch(`/api/ai/clear/${sessionId}`, {
        method: 'POST',
      })
      setMessages([])
    } catch (err) {
      console.error('Failed to clear chat:', err)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // Floating button when collapsed
  if (!isExpanded) {
    return (
      <button
        onClick={() => setIsExpanded(true)}
        className="fixed bottom-6 right-6 w-16 h-16 bg-gradient-to-br from-violet-600 to-indigo-700 
                   rounded-full shadow-xl hover:shadow-2xl transition-all duration-300 
                   flex items-center justify-center text-white z-50 hover:scale-110"
        title="AI Trading Assistant"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        {insights.length > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-amber-500 rounded-full text-xs flex items-center justify-center">
            {insights.length}
          </span>
        )}
      </button>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 w-[420px] h-[600px] bg-slate-900 rounded-2xl shadow-2xl 
                    border border-slate-700/50 flex flex-col z-50 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-violet-600 to-indigo-700 p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div>
            <h3 className="text-white font-semibold">AI Trading Assistant</h3>
            <p className="text-white/70 text-xs flex items-center gap-1">
              <span className={`w-2 h-2 rounded-full ${
                currentProvider === 'ollama' ? 'bg-green-400' : 
                currentProvider === 'anthropic' ? 'bg-orange-400' : 'bg-blue-400'
              }`} />
              {currentProvider === 'ollama' ? 'Ollama (Local)' : 
               currentProvider === 'anthropic' ? 'Claude' : 'GPT-4'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`p-2 hover:bg-white/10 rounded-lg transition-colors ${showSettings ? 'bg-white/20' : ''}`}
            title="LLM Settings"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white/70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
          <button
            onClick={clearChat}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            title="Clear chat"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white/70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
          <button
            onClick={() => setIsExpanded(false)}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Provider Settings Panel */}
      {showSettings && providers && (
        <div className="p-3 bg-slate-800 border-b border-slate-700/50">
          <p className="text-xs text-slate-400 mb-2 font-medium">LLM Provider</p>
          <div className="grid grid-cols-3 gap-2">
            {/* OpenAI */}
            <button
              onClick={() => providers.providers.openai?.available && switchProvider('openai')}
              disabled={!providers.providers.openai?.available}
              className={`p-2 rounded-lg text-xs font-medium transition-all ${
                currentProvider === 'openai' 
                  ? 'bg-blue-600 text-white' 
                  : providers.providers.openai?.available
                    ? 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    : 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
              }`}
              title={providers.providers.openai?.reason || providers.providers.openai?.model}
            >
              <div className="flex flex-col items-center gap-1">
                <span>🤖</span>
                <span>OpenAI</span>
                {currentProvider === 'openai' && <span className="text-[10px] opacity-70">Active</span>}
              </div>
            </button>

            {/* Ollama */}
            <button
              onClick={() => providers.providers.ollama?.available && switchProvider('ollama')}
              disabled={!providers.providers.ollama?.available}
              className={`p-2 rounded-lg text-xs font-medium transition-all ${
                currentProvider === 'ollama' 
                  ? 'bg-green-600 text-white' 
                  : providers.providers.ollama?.available
                    ? 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    : 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
              }`}
              title={providers.providers.ollama?.reason || `Model: ${providers.providers.ollama?.model}`}
            >
              <div className="flex flex-col items-center gap-1">
                <span>🦙</span>
                <span>Ollama</span>
                {currentProvider === 'ollama' && <span className="text-[10px] opacity-70">Local</span>}
              </div>
            </button>

            {/* Anthropic */}
            <button
              onClick={() => providers.providers.anthropic?.available && switchProvider('anthropic')}
              disabled={!providers.providers.anthropic?.available}
              className={`p-2 rounded-lg text-xs font-medium transition-all ${
                currentProvider === 'anthropic' 
                  ? 'bg-orange-600 text-white' 
                  : providers.providers.anthropic?.available
                    ? 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    : 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
              }`}
              title={providers.providers.anthropic?.reason || providers.providers.anthropic?.model}
            >
              <div className="flex flex-col items-center gap-1">
                <span>🧠</span>
                <span>Claude</span>
                {currentProvider === 'anthropic' && <span className="text-[10px] opacity-70">Active</span>}
              </div>
            </button>
          </div>

          {/* Ollama Models */}
          {currentProvider === 'ollama' && providers.providers.ollama?.models && (
            <div className="mt-2 pt-2 border-t border-slate-700">
              <p className="text-[10px] text-slate-500 mb-1">Available Ollama models:</p>
              <div className="flex flex-wrap gap-1">
                {providers.providers.ollama.models.slice(0, 5).map((model) => (
                  <span key={model} className="text-[10px] bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded">
                    {model}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Quick Insights */}
      {insights.length > 0 && messages.length === 0 && (
        <div className="p-3 bg-slate-800/50 border-b border-slate-700/50">
          <p className="text-xs text-slate-400 mb-2 font-medium">Quick Insights</p>
          <div className="flex flex-wrap gap-2">
            {insights.slice(0, 4).map((insight, idx) => (
              <span key={idx} className="text-xs bg-slate-700/50 text-slate-300 px-2 py-1 rounded-md">
                {insight}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <div className="w-16 h-16 mx-auto mb-4 bg-slate-800 rounded-full flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <p className="text-slate-400 text-sm mb-4">Ask me anything about your trading performance!</p>
            <div className="space-y-2">
              <p className="text-xs text-slate-500 mb-2">Try asking:</p>
              {examples.slice(0, 4).map((example, idx) => (
                <button
                  key={idx}
                  onClick={() => sendMessage(example)}
                  className="block w-full text-left text-sm text-slate-400 hover:text-violet-400 
                             bg-slate-800/50 hover:bg-slate-800 px-3 py-2 rounded-lg transition-colors"
                >
                  "{example}"
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-gradient-to-br from-violet-600 to-indigo-700 text-white rounded-br-md'
                  : 'bg-slate-800 text-slate-200 rounded-bl-md'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              <p className={`text-xs mt-1 ${msg.role === 'user' ? 'text-white/50' : 'text-slate-500'}`}>
                {msg.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-700/50 bg-slate-800/50">
        <div className="flex items-center gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about performance, strategies, optimization..."
            className="flex-1 bg-slate-700/50 text-slate-200 placeholder-slate-500 
                       rounded-xl px-4 py-3 text-sm resize-none focus:outline-none 
                       focus:ring-2 focus:ring-violet-500/50 border border-slate-600/50"
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || isLoading}
            className="p-3 bg-gradient-to-br from-violet-600 to-indigo-700 rounded-xl 
                       hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
