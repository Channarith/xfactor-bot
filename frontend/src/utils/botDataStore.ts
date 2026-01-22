/**
 * Bot Performance Data Store
 * 
 * Persists bot performance data to disk when app closes,
 * and reloads it on startup for immediate display.
 * Uses Tauri's store plugin for desktop, falls back to localStorage for web.
 * 
 * @version 2.1.13
 */

// Check if running in Tauri desktop app
const isTauri = typeof window !== 'undefined' && !!(window as any).__TAURI__

// Store keys
const STORE_KEYS = {
  BOTS_SUMMARY: 'bots_summary',
  BOTS_PERFORMANCE: 'bots_performance',
  PORTFOLIO_DATA: 'portfolio_data',
  LAST_SAVED: 'last_saved_timestamp',
} as const

// Type definitions
export interface BotSummary {
  id: string
  name: string
  status: string
  symbols_count: number
  strategies: string[]
  daily_pnl: number
  uptime_seconds: number
}

export interface BotPerformanceData {
  botId: string
  timeRange: string
  data_points: Array<{
    timestamp: string
    value: number
    pnl: number
    pnl_pct: number
  }>
  summary: {
    start_value: number
    end_value: number
    total_pnl: number
    total_pnl_pct: number
    max_drawdown_pct: number
    volatility_pct: number
    num_trades: number
    win_rate: number
  } | null
}

export interface PortfolioData {
  totalValue: number
  dailyPnL: number
  dailyPnLPct: number
  openPositions: number
  exposure: number
  connectedBrokers: Array<{ broker: string; equity: number }>
}

export interface CachedBotData {
  botsSummary: BotSummary[]
  botsPerformance: Record<string, BotPerformanceData>
  portfolioData: PortfolioData | null
  lastSaved: string
  isStale: boolean
}

// Tauri store instance (lazy loaded)
let tauriStore: any = null

/**
 * Initialize Tauri store if in desktop mode
 */
async function getTauriStore() {
  if (!isTauri) return null
  
  if (!tauriStore) {
    try {
      const { Store } = await import('@tauri-apps/plugin-store')
      tauriStore = await Store.load('bot-performance-cache.json')
      console.log('[BotDataStore] Tauri store initialized')
    } catch (e) {
      console.warn('[BotDataStore] Failed to initialize Tauri store:', e)
      return null
    }
  }
  
  return tauriStore
}

/**
 * Save data to storage
 */
async function saveToStorage(key: string, data: any): Promise<void> {
  const store = await getTauriStore()
  
  if (store) {
    try {
      await store.set(key, data)
      await store.save()
      console.log(`[BotDataStore] Saved ${key} to Tauri store`)
    } catch (e) {
      console.warn(`[BotDataStore] Failed to save ${key} to Tauri store:`, e)
      // Fallback to localStorage
      localStorage.setItem(`xfactor_${key}`, JSON.stringify(data))
    }
  } else {
    // Browser mode - use localStorage
    try {
      localStorage.setItem(`xfactor_${key}`, JSON.stringify(data))
      console.log(`[BotDataStore] Saved ${key} to localStorage`)
    } catch (e) {
      console.warn(`[BotDataStore] Failed to save ${key} to localStorage:`, e)
    }
  }
}

/**
 * Load data from storage
 */
async function loadFromStorage<T>(key: string): Promise<T | null> {
  const store = await getTauriStore()
  
  if (store) {
    try {
      const data = await store.get(key)
      if (data !== null && data !== undefined) {
        console.log(`[BotDataStore] Loaded ${key} from Tauri store`)
        return data as T
      }
    } catch (e) {
      console.warn(`[BotDataStore] Failed to load ${key} from Tauri store:`, e)
    }
  }
  
  // Fallback to localStorage
  try {
    const stored = localStorage.getItem(`xfactor_${key}`)
    if (stored) {
      console.log(`[BotDataStore] Loaded ${key} from localStorage`)
      return JSON.parse(stored) as T
    }
  } catch (e) {
    console.warn(`[BotDataStore] Failed to load ${key} from localStorage:`, e)
  }
  
  return null
}

/**
 * Check if cached data is stale (older than threshold)
 */
function isDataStale(lastSaved: string, maxAgeMinutes: number = 60): boolean {
  if (!lastSaved) return true
  
  const savedTime = new Date(lastSaved).getTime()
  const now = Date.now()
  const ageMinutes = (now - savedTime) / (1000 * 60)
  
  return ageMinutes > maxAgeMinutes
}

// ============ Public API ============

/**
 * Save all bot performance data
 */
export async function saveBotPerformanceData(
  botsSummary: BotSummary[],
  botsPerformance: Record<string, BotPerformanceData> = {},
  portfolioData: PortfolioData | null = null
): Promise<void> {
  const timestamp = new Date().toISOString()
  
  console.log('[BotDataStore] Saving bot performance data...', {
    botsCount: botsSummary.length,
    performanceRecords: Object.keys(botsPerformance).length,
    hasPortfolio: !!portfolioData,
  })
  
  await Promise.all([
    saveToStorage(STORE_KEYS.BOTS_SUMMARY, botsSummary),
    saveToStorage(STORE_KEYS.BOTS_PERFORMANCE, botsPerformance),
    saveToStorage(STORE_KEYS.PORTFOLIO_DATA, portfolioData),
    saveToStorage(STORE_KEYS.LAST_SAVED, timestamp),
  ])
  
  console.log('[BotDataStore] Bot performance data saved at', timestamp)
}

/**
 * Load all cached bot performance data
 */
export async function loadBotPerformanceData(): Promise<CachedBotData> {
  console.log('[BotDataStore] Loading cached bot performance data...')
  
  const [botsSummary, botsPerformance, portfolioData, lastSaved] = await Promise.all([
    loadFromStorage<BotSummary[]>(STORE_KEYS.BOTS_SUMMARY),
    loadFromStorage<Record<string, BotPerformanceData>>(STORE_KEYS.BOTS_PERFORMANCE),
    loadFromStorage<PortfolioData>(STORE_KEYS.PORTFOLIO_DATA),
    loadFromStorage<string>(STORE_KEYS.LAST_SAVED),
  ])
  
  const cachedData: CachedBotData = {
    botsSummary: botsSummary || [],
    botsPerformance: botsPerformance || {},
    portfolioData: portfolioData,
    lastSaved: lastSaved || '',
    isStale: isDataStale(lastSaved || ''),
  }
  
  console.log('[BotDataStore] Loaded cached data:', {
    botsCount: cachedData.botsSummary.length,
    performanceRecords: Object.keys(cachedData.botsPerformance).length,
    hasPortfolio: !!cachedData.portfolioData,
    lastSaved: cachedData.lastSaved,
    isStale: cachedData.isStale,
  })
  
  return cachedData
}

/**
 * Clear all cached bot data
 */
export async function clearBotPerformanceData(): Promise<void> {
  console.log('[BotDataStore] Clearing all cached bot data...')
  
  const store = await getTauriStore()
  
  if (store) {
    try {
      await store.clear()
      await store.save()
      console.log('[BotDataStore] Tauri store cleared')
    } catch (e) {
      console.warn('[BotDataStore] Failed to clear Tauri store:', e)
    }
  }
  
  // Also clear localStorage
  Object.values(STORE_KEYS).forEach(key => {
    localStorage.removeItem(`xfactor_${key}`)
  })
  
  console.log('[BotDataStore] All cached bot data cleared')
}

/**
 * Save individual bot performance data
 */
export async function saveSingleBotPerformance(
  botId: string,
  performanceData: BotPerformanceData
): Promise<void> {
  const existing = await loadFromStorage<Record<string, BotPerformanceData>>(STORE_KEYS.BOTS_PERFORMANCE) || {}
  existing[botId] = performanceData
  await saveToStorage(STORE_KEYS.BOTS_PERFORMANCE, existing)
  console.log(`[BotDataStore] Saved performance data for bot ${botId}`)
}

/**
 * Get cached performance data for a specific bot
 */
export async function getBotPerformanceCache(botId: string): Promise<BotPerformanceData | null> {
  const allPerformance = await loadFromStorage<Record<string, BotPerformanceData>>(STORE_KEYS.BOTS_PERFORMANCE)
  return allPerformance?.[botId] || null
}

/**
 * Save portfolio data only
 */
export async function savePortfolioData(portfolioData: PortfolioData): Promise<void> {
  await saveToStorage(STORE_KEYS.PORTFOLIO_DATA, portfolioData)
  await saveToStorage(STORE_KEYS.LAST_SAVED, new Date().toISOString())
  console.log('[BotDataStore] Portfolio data saved')
}

/**
 * Event emitter for cache updates
 */
export function emitCacheLoaded(data: CachedBotData): void {
  window.dispatchEvent(new CustomEvent('bot-cache-loaded', { detail: data }))
}

export function emitCacheSaved(): void {
  window.dispatchEvent(new CustomEvent('bot-cache-saved'))
}

/**
 * Format last saved time for display
 */
export function formatLastSaved(lastSaved: string): string {
  if (!lastSaved) return 'Never'
  
  const savedDate = new Date(lastSaved)
  const now = new Date()
  const diffMs = now.getTime() - savedDate.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMins / 60)
  
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  
  return savedDate.toLocaleDateString()
}
