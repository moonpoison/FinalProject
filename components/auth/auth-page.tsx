"use client"

import { useState } from "react"
import { useAuth } from "@/contexts/auth-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Eye, EyeOff } from "lucide-react"

type AuthMode = "login" | "signup"

export function AuthPage() {
  const { login, signup, isLoading } = useAuth()
  const [mode, setMode] = useState<AuthMode>("login")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [name, setName] = useState("")
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState("")

  const reset = (next: AuthMode) => {
    setMode(next)
    setError("")
    setEmail("")
    setPassword("")
    setConfirmPassword("")
    setName("")
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (mode === "signup") {
      if (name.trim().length < 2) return setError("이름을 2자 이상 입력해주세요.")
      if (password.length < 8) return setError("비밀번호는 8자 이상이어야 합니다.")
      if (password !== confirmPassword) return setError("비밀번호가 일치하지 않습니다.")
      // Always signup as "buyer", role can be changed later in settings
      const res = await signup(email, password, name.trim(), "buyer")
      if (res.error) setError(res.error)
    } else {
      const res = await login(email, password)
      if (res.error) setError(res.error)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-10">
          <div className="w-10 h-10 rounded-2xl bg-foreground flex items-center justify-center">
            <span className="text-lg font-bold text-background">A</span>
          </div>
          <span className="text-xl font-bold">AutoFlow</span>
        </div>

        <div className="bg-card border rounded-3xl shadow-sm overflow-hidden">
          {/* Tab */}
          <div className="flex border-b">
            {(["login", "signup"] as AuthMode[]).map((m) => (
              <button
                key={m}
                onClick={() => reset(m)}
                className={`flex-1 py-4 text-sm font-semibold transition-colors ${
                  mode === m
                    ? "text-foreground border-b-2 border-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {m === "login" ? "로그인" : "회원가입"}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {mode === "signup" && (
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">이름</label>
                <Input
                  placeholder="홍길동"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="rounded-xl h-11"
                  required
                  autoFocus
                />
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">이메일</label>
              <Input
                type="email"
                placeholder="example@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="rounded-xl h-11"
                required
                autoFocus={mode === "login"}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">비밀번호</label>
              <div className="relative">
                <Input
                  type={showPw ? "text" : "password"}
                  placeholder={mode === "signup" ? "8자 이상" : "비밀번호"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="rounded-xl h-11 pr-10"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {mode === "signup" && (
              <>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">비밀번호 확인</label>
                  <Input
                    type="password"
                    placeholder="비밀번호 재입력"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="rounded-xl h-11"
                    required
                  />
                </div>
              </>
            )}

            {error && (
              <p className="text-xs text-destructive bg-destructive/10 px-3 py-2 rounded-xl">
                {error}
              </p>
            )}

            <Button
              type="submit"
              className="w-full h-11 rounded-xl font-semibold text-sm mt-2"
              disabled={isLoading}
            >
              {isLoading ? "처리 중..." : mode === "login" ? "로그인" : "회원가입"}
            </Button>

          </form>
        </div>
      </div>
    </div>
  )
}
