import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface AuthContextType {
  token: string
  isAuthenticated: boolean
  isOfflineMode: boolean
  login: (password: string) => Promise<boolean>
  logout: () => Promise<void>
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
    // Try to restore token from localStorage
    return localStorage.getItem('admin_token') || ''
  })
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isOfflineMode, setIsOfflineMode] = useState(false)

  // Verify token on mount
  useEffect(() => {
    if (token) {
      verifyToken(token)
    }
  }, [])

  const verifyToken = async (authToken: string) => {
    // Check if it's an offline token
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
        // Token expired or invalid
        setToken('')
        setIsAuthenticated(false)
        setIsOfflineMode(false)
        localStorage.removeItem('admin_token')
      }
    } catch (e) {
      console.error('[Auth] Token verification failed (backend may be down):', e)
      // If we have an offline token, keep it valid
      if (authToken.startsWith('offline_')) {
        setIsAuthenticated(true)
        setIsOfflineMode(true)
      } else {
        // Backend unreachable, but don't clear token - might reconnect later
        setIsAuthenticated(false)
      }
    }
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
    <AuthContext.Provider value={{ token, isAuthenticated, isOfflineMode, login, logout }}>
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

