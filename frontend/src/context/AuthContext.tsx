import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface AuthContextType {
  token: string
  isAuthenticated: boolean
  isOfflineMode: boolean
  login: (password: string) => Promise<boolean>
  logout: () => Promise<void>
  /** Call when an API returns 401 so we clear saved auth and show unlock again */
  markUnauthorized: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

// Offline fallback password for admin panel
const OFFLINE_ADMIN_PASSWORD = '106431'

// Generate a simple offline token
const generateOfflineToken = (): string => {
  const timestamp = Date.now()
  const random = Math.random().toString(36).substring(2)
  return `offline_${timestamp}_${random}`
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string>(() => {
    return localStorage.getItem('admin_token') || ''
  })
  // Recognize saved admin login immediately so pre-connected unlock is not lost (e.g. before broker connect)
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    const saved = localStorage.getItem('admin_token') || ''
    return saved.length > 0
  })
  const [isOfflineMode, setIsOfflineMode] = useState(false)

  // Verify token on mount; only clear auth when backend explicitly says invalid (401), not on network error
  useEffect(() => {
    if (token) {
      verifyToken(token)
    }
  }, [])

  const verifyToken = async (authToken: string) => {
    if (authToken.startsWith('offline_')) {
      console.log('[Auth] Using offline token')
      setIsAuthenticated(true)
      setIsOfflineMode(true)
      return
    }
    
    try {
      const res = await fetch('/api/admin/verify', {
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (res.ok) {
        setIsAuthenticated(true)
        setIsOfflineMode(false)
      } else {
        // Backend explicitly rejected token (expired/invalid)
        setToken('')
        setIsAuthenticated(false)
        setIsOfflineMode(false)
        localStorage.removeItem('admin_token')
      }
    } catch (e) {
      console.error('[Auth] Token verification failed (backend may be down):', e)
      // Network error: keep current auth state so pre-connected admin login is not lost
      if (authToken.startsWith('offline_')) {
        setIsAuthenticated(true)
        setIsOfflineMode(true)
      }
      // For backend-issued tokens, leave isAuthenticated as-is (we started true if token existed)
    }
  }

  const markUnauthorized = () => {
    setToken('')
    setIsAuthenticated(false)
    setIsOfflineMode(false)
    localStorage.removeItem('admin_token')
    console.log('[Auth] Marked unauthorized (e.g. API returned 401)')
  }

  const login = async (password: string): Promise<boolean> => {
    // First, try the backend API
    try {
      const res = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      
      if (res.ok) {
        const data = await res.json()
        setToken(data.token)
        setIsAuthenticated(true)
        setIsOfflineMode(false)
        localStorage.setItem('admin_token', data.token)
        console.log('[Auth] Login successful via backend API')
        return true
      }
      
      // Backend returned error (e.g., wrong password)
      // Fall through to offline check
    } catch (e) {
      console.warn('[Auth] Backend login failed (may be offline):', e)
      // Backend is unreachable, try offline login
    }
    
    // Fallback: Offline login with hardcoded password
    // This allows admin panel access even when backend is down
    if (password === OFFLINE_ADMIN_PASSWORD) {
      const offlineToken = generateOfflineToken()
      setToken(offlineToken)
      setIsAuthenticated(true)
      setIsOfflineMode(true)
      localStorage.setItem('admin_token', offlineToken)
      console.log('[Auth] Login successful via offline mode')
      return true
    }
    
    console.log('[Auth] Login failed - invalid password')
    return false
  }

  const logout = async () => {
    // Try to logout from backend (ignore errors)
    if (token && !token.startsWith('offline_')) {
      try {
        await fetch('/api/admin/logout', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        })
      } catch (e) {
        console.warn('[Auth] Logout request failed (backend may be down):', e)
      }
    }
    
    setToken('')
    setIsAuthenticated(false)
    setIsOfflineMode(false)
    localStorage.removeItem('admin_token')
    console.log('[Auth] Logged out')
  }

  return (
    <AuthContext.Provider value={{ token, isAuthenticated, isOfflineMode, login, logout, markUnauthorized }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

