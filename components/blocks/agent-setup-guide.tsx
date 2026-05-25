"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Download, Copy, Check, Monitor, Terminal, ChevronDown, ChevronUp } from "lucide-react"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"

interface AgentSetupGuideProps {
  compact?: boolean
}

type Platform = "mac" | "windows" | "linux"

function detectPlatform(): Platform {
  if (typeof navigator === "undefined") return "mac"
  const ua = navigator.userAgent
  if (ua.includes("Mac")) return "mac"
  if (ua.includes("Win")) return "windows"
  return "linux"
}

const PLATFORM_LABELS: Record<Platform, string> = {
  mac: "macOS",
  windows: "Windows",
  linux: "Linux",
}

export function AgentSetupGuide({ compact = false }: AgentSetupGuideProps) {
  const [platform, setPlatform] = useState<Platform>("mac")
  const [agentToken, setAgentToken] = useState<string>("")
  const [copied, setCopied] = useState(false)
  const [tokenLoading, setTokenLoading] = useState(false)
  const [expanded, setExpanded] = useState(!compact)
  const [downloads, setDownloads] = useState<Record<string, string>>({})
  const [version, setVersion] = useState("")

  useEffect(() => {
    setPlatform(detectPlatform())
    loadAgentInfo()
  }, [])

  async function loadAgentInfo() {
    try {
      const info = await api.getAgentVersion()
      setVersion(info.version)
      setDownloads(info.downloads || {})
    } catch {
      // 서버 미연결 시 무시
    }
  }

  async function handleGenerateToken() {
    setTokenLoading(true)
    try {
      const result = await api.generateAgentToken()
      setAgentToken(result.token)
    } catch {
      setAgentToken("토큰 생성 실패. 로그인 상태를 확인해주세요.")
    } finally {
      setTokenLoading(false)
    }
  }

  async function handleCopyToken() {
    if (!agentToken) return
    try {
      await navigator.clipboard.writeText(agentToken)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback
      const textarea = document.createElement("textarea")
      textarea.value = agentToken
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand("copy")
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  function handleDownload() {
    const downloadUrl = downloads[platform]
    if (downloadUrl) {
      // GitHub Releases 등 외부 URL이면 그대로, 상대 경로면 API base 붙이기
      if (downloadUrl.startsWith("http")) {
        window.open(downloadUrl, "_blank")
      } else {
        window.open(api.getAgentDownloadUrl(platform), "_blank")
      }
    } else {
      // 어떤 다운로드도 없으면 기본 API
      window.open(api.getAgentDownloadUrl(platform), "_blank")
    }
  }

  if (compact && !expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs text-orange-600 hover:bg-orange-500/5 rounded-xl transition-colors"
      >
        <span>에이전트 설치 가이드</span>
        <ChevronDown className="w-3.5 h-3.5" />
      </button>
    )
  }

  return (
    <div className={cn("space-y-3", compact ? "px-1" : "")}>
      {/* 헤더 */}
      {compact && (
        <button
          onClick={() => setExpanded(false)}
          className="w-full flex items-center justify-between text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <span className="font-medium">에이전트 설치 가이드</span>
          <ChevronUp className="w-3.5 h-3.5" />
        </button>
      )}

      {!compact && (
        <div className="flex items-center gap-2">
          <Monitor className="w-4 h-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">로컬 에이전트</h3>
          {version && (
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
              v{version}
            </span>
          )}
        </div>
      )}

      {/* OS 선택 */}
      <div className="flex gap-1.5">
        {(["mac", "windows", "linux"] as Platform[]).map((p) => (
          <button
            key={p}
            onClick={() => setPlatform(p)}
            className={cn(
              "px-3 py-1.5 text-xs rounded-lg transition-colors",
              platform === p
                ? "bg-primary text-primary-foreground"
                : "bg-muted/50 text-muted-foreground hover:bg-muted"
            )}
          >
            {PLATFORM_LABELS[p]}
          </button>
        ))}
      </div>

      {/* 설치 단계 */}
      <div className="space-y-2.5">
        {/* Step 1: 다운로드 */}
        <div className="flex items-start gap-2.5">
          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-bold">
            1
          </span>
          <div className="flex-1 space-y-1.5">
            <p className={cn("font-medium", compact ? "text-xs" : "text-sm")}>에이전트 다운로드</p>
            <Button
              onClick={handleDownload}
              size="sm"
              className="w-full rounded-xl h-8 text-xs"
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              {PLATFORM_LABELS[platform]}용 다운로드
            </Button>
          </div>
        </div>

        {/* Step 2: 토큰 생성 */}
        <div className="flex items-start gap-2.5">
          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-bold">
            2
          </span>
          <div className="flex-1 space-y-1.5">
            <p className={cn("font-medium", compact ? "text-xs" : "text-sm")}>연결 토큰 복사</p>
            {!agentToken ? (
              <Button
                onClick={handleGenerateToken}
                disabled={tokenLoading}
                variant="outline"
                size="sm"
                className="w-full rounded-xl h-8 text-xs"
              >
                {tokenLoading ? "생성 중..." : "토큰 생성"}
              </Button>
            ) : (
              <div className="flex gap-1.5">
                <div className="flex-1 bg-muted/50 rounded-lg px-2.5 py-1.5 text-[10px] font-mono truncate">
                  {agentToken.slice(0, 30)}...
                </div>
                <Button
                  onClick={handleCopyToken}
                  variant="outline"
                  size="sm"
                  className="rounded-lg h-7 px-2"
                >
                  {copied ? (
                    <Check className="w-3.5 h-3.5 text-green-500" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Step 3: 실행 */}
        <div className="flex items-start gap-2.5">
          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-bold">
            3
          </span>
          <div className="flex-1 space-y-1.5">
            <p className={cn("font-medium", compact ? "text-xs" : "text-sm")}>에이전트 실행</p>
            <div className="bg-muted/50 rounded-lg px-3 py-2">
              <div className="flex items-center gap-1.5 mb-1">
                <Terminal className="w-3 h-3 text-muted-foreground" />
                <span className="text-[10px] text-muted-foreground">터미널</span>
              </div>
              <code className="text-[10px] font-mono text-foreground/80 break-all">
                {downloads[platform]
                  ? `./AutoFlowAgent --token <토큰>`
                  : `python AutoFlowAgent.py --token <토큰>`
                }
              </code>
            </div>
          </div>
        </div>
      </div>

      {/* macOS 보안 안내 */}
      {platform === "mac" && downloads[platform] && (
        <p className="text-[10px] text-muted-foreground/70 leading-relaxed">
          macOS에서 &quot;확인되지 않은 개발자&quot; 경고가 나오면 터미널에서{" "}
          <code className="bg-muted px-1 rounded">xattr -d com.apple.quarantine ./AutoFlowAgent*</code>{" "}
          실행 후 다시 시도하세요.
        </p>
      )}
    </div>
  )
}
