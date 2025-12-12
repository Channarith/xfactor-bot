import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface AuthContextType {
  token: string
  isAuthenticated: boolean
  login: (password: string) => Promise<boolean>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string>(() => {
    // Try to restore token from localStorage
    return localStorage.getItem('admin_token') || ''
  })
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // Verify token on mount
  useEffect(() => {
    if (token) {
      verifyToken(token)
    }
  }, [])

  const verifyToken = async (authToken: string) => {
    try {
      const res = await fetch('/api/admin/verify', {
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (res.ok) {
        setIsAuthenticated(true)
      } else {
        // Token expired or invalid
        setToken('')
        setIsAuthenticated(false)
        localStorage.removeItem('admin_token')
      }
    } catch (e) {
      console.error('Token verification failed:', e)
      setIsAuthenticated(false)
    }
  }

  const login = async (password: string): Promise<boolean> => {
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
        localStorage.setItem('admin_token', data.token)
        return true
      }
      return false
    } catch (e) {
      console.error('Login failed:', e)
      return false
    }
  }

  const logout = async () => {
    try {
      if (token) {
        await fetch('/api/admin/logout', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        })
      }
    } catch (e) {
      console.error('Logout request failed:', e)
    }
    
    setToken('')
    setIsAuthenticated(false)
    localStorage.removeItem('admin_token')
  }

  return (
    <AuthContext.Provider value={{ token, isAuthenticated, login, logout }}>
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

