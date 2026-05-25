"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Wifi, WifiOff, Trash2, Download, Play, Square, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import type { WorkspaceBlock } from "@/types/blocks"
import { AgentSetupGuide } from "./agent-setup-guide"

interface LogEntry {
  id: string
  time: string
  message: string
  type: "info" | "success" | "error" | "warning"
}

function formatTime(date: Date): string {
  const h = String(date.getHours()).padStart(2, "0")
  const m = String(date.getMinutes()).padStart(2, "0")
  const s = String(date.getSeconds()).padStart(2, "0")
  return `${h}:${m}:${s}`
}

interface ExecutionPanelProps {
  isConnected: boolean
  onConnect: () => void
  blocks?: WorkspaceBlock[]
  workspaceName?: string
  variables?: Record<string, string>
  prompt?: string  // AI 생성 시 원본 프롬프트 (지식베이스 참조용)
}

export function ExecutionPanel({ isConnected, onConnect, blocks = [], workspaceName = "automation", variables = {}, prompt }: ExecutionPanelProps) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [currentCommandId, setCurrentCommandId] = useState<string | null>(null)
  const logEndRef = useRef<HTMLDivElement>(null)
  const statusPollRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    setLogs([{ id: "init", time: formatTime(new Date()), message: "시스템 준비 완료", type: "info" }])
  }, [])

  // 컴포넌트 언마운트 시 폴링 정리
  useEffect(() => {
    return () => {
      if (statusPollRef.current) {
        clearInterval(statusPollRef.current)
      }
    }
  }, [])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [logs])

  function addLog(message: string, type: LogEntry["type"] = "info") {
    setLogs((prev) => [
      ...prev,
      { id: `${Date.now()}-${Math.random()}`, time: formatTime(new Date()), message, type },
    ])
  }

  // 변수를 블록에 적용
  function applyVariablesToBlocks(blocks: WorkspaceBlock[], variables: Record<string, string>): WorkspaceBlock[] {
    if (!variables || Object.keys(variables).length === 0) return blocks

    return blocks.map((block) => {
      const newFieldValues = { ...block.fieldValues }

      Object.entries(newFieldValues).forEach(([key, value]) => {
        if (typeof value === "string") {
          let newValue = value
          Object.entries(variables).forEach(([varName, varValue]) => {
            const patterns = [
              new RegExp(`\\{\\{\\s*${varName}\\s*\\}\\}`, "gi"),
              new RegExp(`\\{\\s*${varName}\\s*\\}`, "gi"),
            ]
            patterns.forEach((pattern) => {
              newValue = newValue.replace(pattern, varValue)
            })
          })
          newFieldValues[key] = newValue
        }
      })

      return { ...block, fieldValues: newFieldValues }
    })
  }

  // 실행 상태 폴링
  const pollExecutionStatus = useCallback((commandId: string) => {
    statusPollRef.current = setInterval(async () => {
      try {
        const status = await api.getExecutionStatus(commandId)
        if (status.status === "completed" || status.success !== undefined) {
          // 실행 완료
          setIsRunning(false)
          setCurrentCommandId(null)
          if (statusPollRef.current) {
            clearInterval(statusPollRef.current)
          }
          if (status.success) {
            addLog("자동화 실행 완료", "success")
          } else {
            addLog(`실행 실패: ${status.error || "알 수 없는 오류"}`, "error")
          }
        } else if (status.status === "not_found") {
          // 명령 없음 - 폴링 중단
          setIsRunning(false)
          setCurrentCommandId(null)
          if (statusPollRef.current) {
            clearInterval(statusPollRef.current)
          }
        }
      } catch (error) {
        console.error("Status poll error:", error)
      }
    }, 2000) // 2초마다 폴링
  }, [])

  // 실행 시작
  const handleRun = async () => {
    if (blocks.length === 0) {
      addLog("실행할 블록이 없습니다", "warning")
      return
    }

    if (!isConnected) {
      addLog("로컬 에이전트가 연결되지 않았습니다", "error")
      return
    }

    const appliedBlocks = applyVariablesToBlocks(blocks, variables)
    const varCount = Object.keys(variables).filter(k => variables[k]).length
    if (varCount > 0) {
      addLog(`변수 ${varCount}개 적용됨`, "info")
    }

    addLog("자동화 실행 요청 중...", "info")
    setIsRunning(true)

    try {
      const response = await api.queueExecution(appliedBlocks, workspaceName)
      if (response.success && response.command_id) {
        setCurrentCommandId(response.command_id)
        addLog(`실행 명령 전송됨 (ID: ${response.command_id.slice(0, 8)}...)`, "success")
        addLog("로컬 에이전트에서 실행 중...", "info")
        pollExecutionStatus(response.command_id)
      } else {
        setIsRunning(false)
        addLog("실행 요청 실패", "error")
      }
    } catch (error) {
      setIsRunning(false)
      addLog(`실행 요청 실패: ${error instanceof Error ? error.message : "오류"}`, "error")
    }
  }

  // 실행 중단
  const handleStop = async () => {
    if (!currentCommandId) {
      addLog("중단할 실행이 없습니다", "warning")
      return
    }

    addLog("중단 요청 중...", "info")

    try {
      const response = await api.stopExecution(currentCommandId)
      if (response.success) {
        addLog(`실행 중단됨: ${response.message}`, "warning")
        setIsRunning(false)
        setCurrentCommandId(null)
        if (statusPollRef.current) {
          clearInterval(statusPollRef.current)
        }
      }
    } catch (error) {
      addLog(`중단 요청 실패: ${error instanceof Error ? error.message : "오류"}`, "error")
    }
  }

  const handleDownloadCode = async () => {
    if (blocks.length === 0) {
      addLog("다운로드할 블록이 없습니다", "warning")
      return
    }

    const appliedBlocks = applyVariablesToBlocks(blocks, variables)
    const varCount = Object.keys(variables).filter(k => variables[k]).length
    if (varCount > 0) {
      addLog(`변수 ${varCount}개 적용됨`, "info")
    }

    addLog("Python 코드 생성 중...", "info")

    try {
      const response = await api.generateCode(appliedBlocks, workspaceName, prompt)
      if (response.success && response.code) {
        const blob = new Blob([response.code], { type: "text/x-python" })
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `${workspaceName}.py`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)

        addLog(`코드 다운로드 완료 (${response.block_count}개 블록)`, "success")
      }
    } catch (error) {
      addLog(`코드 생성 실패: ${error instanceof Error ? error.message : "오류"}`, "error")
    }
  }

  const logColor = (type: LogEntry["type"]) => {
    switch (type) {
      case "success": return "text-green-500"
      case "error":   return "text-red-500"
      case "warning": return "text-yellow-500"
      default:        return "text-blue-400"
    }
  }

  return (
    <div className="h-full flex flex-col p-4 gap-3">
      {/* Agent Connection Status */}
      <div
        className={cn(
          "flex items-center gap-2 px-4 py-3 rounded-2xl",
          isConnected ? "bg-green-500/10" : "bg-orange-500/10"
        )}
      >
        {isConnected ? (
          <Wifi className="w-4 h-4 text-green-500" />
        ) : (
          <WifiOff className="w-4 h-4 text-orange-500" />
        )}
        <span className={cn("text-sm font-medium", isConnected ? "text-green-600" : "text-orange-600")}>
          {isConnected ? "로컬 에이전트 연결됨" : "에이전트 미연결"}
        </span>
      </div>

      {/* 에이전트 미연결 시 설치 가이드 */}
      {!isConnected && (
        <AgentSetupGuide compact />
      )}


      {/* Run / Stop Buttons */}
      <div className="flex gap-2">
        {!isRunning ? (
          <Button
            onClick={handleRun}
            disabled={blocks.length === 0 || !isConnected}
            className="flex-1 rounded-2xl h-10 font-medium bg-green-600 hover:bg-green-700"
          >
            <Play className="w-4 h-4 mr-2" />
            실행
          </Button>
        ) : (
          <Button
            onClick={handleStop}
            variant="destructive"
            className="flex-1 rounded-2xl h-10 font-medium"
          >
            <Square className="w-4 h-4 mr-2" />
            중단
          </Button>
        )}
      </div>

      {/* Running Indicator */}
      {isRunning && (
        <div className="flex items-center gap-2 px-4 py-2 bg-blue-500/10 rounded-2xl">
          <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
          <span className="text-sm text-blue-600 font-medium">실행 중...</span>
        </div>
      )}

      {/* Download Code */}
      <Button
        onClick={handleDownloadCode}
        disabled={blocks.length === 0 || isRunning}
        variant="outline"
        className="w-full rounded-2xl h-10 font-medium"
      >
        <Download className="w-4 h-4 mr-2" />
        Python 코드 다운로드
      </Button>

      {/* Block Count */}
      <div className="flex items-center gap-2 px-1">
        <div className={cn("w-2 h-2 rounded-full", blocks.length > 0 ? "bg-blue-500" : "bg-muted-foreground/30")} />
        <span className="text-xs text-muted-foreground">
          {blocks.length}개 블록
        </span>
      </div>

      {/* Logs */}
      <div className="flex-1 overflow-hidden flex flex-col gap-2">
        <div className="flex items-center justify-between px-1">
          <h3 className="text-sm font-semibold">로그</h3>
          <button
            onClick={() => setLogs([])}
            className="text-muted-foreground/50 hover:text-muted-foreground transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto bg-muted/30 rounded-2xl p-3 space-y-1.5 font-mono text-xs">
          {logs.map((log) => (
            <div key={log.id} className={cn("flex gap-2", logColor(log.type))}>
              <span className="text-muted-foreground/40 shrink-0">{log.time}</span>
              <span>{log.message}</span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  )
}
