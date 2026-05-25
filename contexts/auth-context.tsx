"use client"

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react"
import { api, type UserResponse } from "@/lib/api"

export type UserRole = "buyer" | "seller"

export interface AuthUser {
  id: string
  email: string
  name: string
  role: UserRole
  avatar?: string
  joinedAt: string
}

interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<{ error?: string }>
  signup: (email: string, password: string, name: string, role: UserRole) => Promise<{ error?: string }>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function userResponseToAuthUser(user: UserResponse): AuthUser {
  return {
    id: user.id,
    email: user.email,
    name: user.name,
    role: user.role as UserRole,
    avatar: user.avatar || undefined,
    joinedAt: user.joined_at,
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = api.getToken()
    if (token) {
      api.getMe()
        .then((userData) => {
          setUser(userResponseToAuthUser(userData))
        })
        .catch(() => {
          api.setToken(null)
        })
        .finally(() => {
          setIsLoading(false)
        })
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true)
    try {
      const response = await api.login(email, password)
      setUser(userResponseToAuthUser(response.user))
      return {}
    } catch (error) {
      return { error: error instanceof Error ? error.message : "로그인에 실패했습니다." }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const signup = useCallback(
    async (email: string, password: string, name: string, role: UserRole) => {
      setIsLoading(true)
      try {
        const response = await api.signup(email, password, name, role)
        setUser(userResponseToAuthUser(response.user))
        return {}
      } catch (error) {
        return { error: error instanceof Error ? error.message : "회원가입에 실패했습니다." }
      } finally {
        setIsLoading(false)
      }
    },
    []
  )

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } finally {
      setUser(null)
    }
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
