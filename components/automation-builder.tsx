"use client"

import { useState, useCallback, useRef, useEffect } from "react"
import { MultiWorkspace, type MultiWorkspaceHandle } from "@/components/builder/multi-workspace"
import { MarketplacePage } from "@/components/marketplace/marketplace-page"
import { MarketplaceDetailPage } from "@/components/marketplace/marketplace-detail-page"
import { MyPage } from "@/components/mypage/my-page"
import { AICreateDialog } from "@/components/blocks/ai-create-dialog"
import { AIPreviewModal, type AIPreviewData } from "@/components/blocks/ai-preview-modal"
import { VideoUploadModal } from "@/components/blocks/video-upload-modal"
import { SellModal } from "@/components/marketplace/sell-modal"
import { AuthPage } from "@/components/auth/auth-page"
import { ChatPage } from "@/components/chat/chat-page"
import { useAuth } from "@/contexts/auth-context"
import { useChat } from "@/contexts/chat-context"
import { Store, Wrench, User, MessageSquare, LogOut, Plus } from "lucide-react"
import { BLOCK_DEFINITIONS, type WorkspaceBlock } from "@/types/blocks"
import { api } from "@/lib/api"
import type { AutomationItem } from "@/data/marketplace"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"

type View = "builder" | "marketplace" | "market-detail" | "mypage" | "chat"

interface WorkspaceSnapshot {
  id: string
  name: string
  blocks: WorkspaceBlock[]
}

export function AutomationBuilder() {
  // *** IMPORTANT: All hooks must be called before any conditional returns ***
  const { user, isLoading, logout } = useAuth()
  const { unreadCount } = useChat()

  const [view, setView] = useState<View>("builder")
  const [selectedMarketItem, setSelectedMarketItem] = useState<AutomationItem | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [showSellModal, setShowSellModal] = useState(false)
  const [showVideoModal, setShowVideoModal] = useState(false)
  const [showNewWorkspaceDialog, setShowNewWorkspaceDialog] = useState(false)
  const [newWorkspaceName, setNewWorkspaceName] = useState("")
  const [pendingBlocks, setPendingBlocks] = useState<WorkspaceBlock[] | null>(null)
  const [pendingPrompt, setPendingPrompt] = useState<string>("")  // AI 생성 시 원본 프롬프트
  const [generatedBlocks, setGeneratedBlocks] = useState<WorkspaceBlock[] | null>(null)
  const [previewData, setPreviewData] = useState<AIPreviewData>({
    taskName: "",
    summary: "",
    groups: [],
    confidence: 0,
  })
  const workspacesRef = useRef<WorkspaceSnapshot[]>([])
  const multiWorkspaceHandleRef = useRef<MultiWorkspaceHandle | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // 웹소켓으로 에이전트 연결 상태 확인
  useEffect(() => {
    console.log("[WS] useEffect triggered, user:", user?.email)
    if (!user) {
      console.log("[WS] No user, skipping")
      return
    }

    const token = localStorage.getItem("auth_token")
    console.log("[WS] Token exists:", !!token)
    if (!token) return

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"
    const wsBase = apiUrl.replace("http://", "ws://").replace("https://", "wss://").replace("/api", "")
    const wsUrl = `${wsBase}/ws/browser?token=${token}`
    console.log("[WS] Connecting to:", wsUrl)

    const connect = () => {
      try {
        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => {
          console.log("[WS] Browser connected")
          // 에이전트 상태 확인 요청
          ws.send(JSON.stringify({ type: "check_agent" }))
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === "status") {
              setIsConnected(data.agent_connected)
            } else if (data.type === "agent_connected") {
              setIsConnected(true)
            } else if (data.type === "agent_disconnected") {
              setIsConnected(false)
            }
          } catch (e) {
            console.error("[WS] Parse error:", e)
          }
        }

        ws.onclose = () => {
          console.log("[WS] Browser disconnected, reconnecting...")
          setIsConnected(false)
          setTimeout(connect, 5000)
        }

        ws.onerror = (err) => {
          console.error("[WS] Error:", err)
        }
      } catch (e) {
        console.error("[WS] Connection error:", e)
        setTimeout(connect, 5000)
      }
    }

    connect()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [user])

  const handleWorkspacesChange = useCallback((snapshots: WorkspaceSnapshot[]) => {
    workspacesRef.current = snapshots
  }, [])

  const handleMarketItemClick = (item: AutomationItem) => {
    setSelectedMarketItem(item)
    setView("market-detail")
  }

  const handleMarketImport = useCallback((item: AutomationItem, blocksData?: any[]) => {
    const ts = Date.now()
    let blocks: WorkspaceBlock[] = []

    if (blocksData && blocksData.length > 0) {
      // 실제 blocks_data 사용
      blocks = blocksData.map((b: any, i: number) => {
        const def = BLOCK_DEFINITIONS.find((d) => d.id === b.id)
        return {
          id: def?.id || b.id,
          type: def?.type || b.type,
          category: (def?.category || b.category) as any,
          label: def?.label || b.label,
          icon: def?.icon || b.icon,
          color: def?.color || b.color,
          fields: def?.fields || b.fields || [],
          instanceId: b.instanceId || `${b.id}-${ts + i}`,
          fieldValues: b.fieldValues || {},
          groupId: b.groupId,
          groupLabel: b.groupLabel,
          groupColor: b.groupColor,
        } as WorkspaceBlock
      })
    } else {
      // 기본 블록 (fallback)
      const ids = ["start", "open-site", "extract-list", "save-excel"]
      blocks = ids
        .map((id) => BLOCK_DEFINITIONS.find((b) => b.id === id))
        .filter((b): b is (typeof BLOCK_DEFINITIONS)[number] => Boolean(b))
        .map((def, i) => ({ ...def, instanceId: `${def.id}-${ts + i}`, fieldValues: {} }))
    }

    // 새 워크스페이스 이름 입력 다이얼로그 표시
    setPendingBlocks(blocks)
    setNewWorkspaceName(item.title || "마켓플레이스 자동화")
    setShowNewWorkspaceDialog(true)
  }, [])

  const [streamingGroups, setStreamingGroups] = useState<AIPreviewData["groups"]>([])
  const [streamingInfo, setStreamingInfo] = useState<{ taskName: string; summary: string; confidence: number; totalGroups: number } | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const abortStreamRef = useRef<(() => void) | null>(null)

  const handleAIAnalyze = (prompt: string) => {
    setIsAnalyzing(true)
    setIsStreaming(true)
    setStreamingGroups([])
    setStreamingInfo(null)
    setShowCreateDialog(false)
    setShowPreview(true)

    abortStreamRef.current = api.analyzePromptStream(
      prompt,
      // onInfo
      (info) => {
        setStreamingInfo({
          taskName: info.task_name,
          summary: info.summary,
          confidence: info.confidence,
          totalGroups: info.total_groups,
        })
      },
      // onGroup
      (index, group) => {
        console.log("=== Received group ===", index)
        console.log("Full group data:", JSON.stringify(group, null, 2))
        console.log("Steps with field_values:", group.steps.map((s: any) => ({
          id: s.id,
          block_type: s.block_type,
          field_values: s.field_values,
          hasFieldValues: !!s.field_values && Object.keys(s.field_values).length > 0
        })))

        const mappedSteps = group.steps.map((s: any) => {
          const stepData = {
            id: s.id,
            label: s.label,
            description: s.description,
            blockType: s.block_type,
            color: s.color,
            fieldValues: s.field_values || {},
          }
          console.log(`Mapped step ${s.id}:`, stepData)
          return stepData
        })

        setStreamingGroups((prev) => [
          ...prev,
          {
            id: group.id,
            label: group.label,
            description: group.description,
            color: group.color,
            steps: mappedSteps,
          },
        ])
      },
      // onDone
      () => {
        setIsAnalyzing(false)
        setIsStreaming(false)
      },
      // onError
      (error) => {
        console.error("AI 분석 오류:", error)
        setIsAnalyzing(false)
        setIsStreaming(false)
      }
    )
  }

  // Update previewData when streaming completes
  useEffect(() => {
    if (!isStreaming && streamingInfo && streamingGroups.length > 0) {
      setPreviewData({
        taskName: streamingInfo.taskName,
        summary: streamingInfo.summary,
        confidence: streamingInfo.confidence,
        groups: streamingGroups,
      })
    }
  }, [isStreaming, streamingInfo, streamingGroups])

  const handleGenerateBlocks = async () => {
    try {
      // 로컬에서 직접 블록 생성 (field_values 포함)
      const ts = Date.now()
      const blocks: WorkspaceBlock[] = []

      console.log("PreviewData groups:", previewData.groups)
      console.log("StreamingGroups:", streamingGroups)

      for (const group of previewData.groups) {
        console.log("Processing group:", group.label, "steps:", group.steps)
        for (const step of group.steps) {
          console.log("Step:", step.blockType, "fieldValues:", step.fieldValues)
          const def = BLOCK_DEFINITIONS.find((d) => d.id === step.blockType)
          if (def) {
            const block = {
              id: def.id,
              type: def.type,
              category: def.category,
              label: def.label,
              icon: def.icon,
              color: def.color,
              fields: def.fields,
              instanceId: `${def.id}-${ts + blocks.length}`,
              fieldValues: step.fieldValues || {}, // AI가 채워준 필드 값 사용
              groupId: group.id,
              groupLabel: group.label,
              groupColor: group.color,
            }
            console.log("Created block with fieldValues:", block.fieldValues)
            blocks.push(block)
          }
        }
      }

      console.log("Final blocks:", blocks.map(b => ({ id: b.id, fieldValues: b.fieldValues })))

      // 새 워크스페이스 이름 입력 다이얼로그 표시
      setPendingBlocks(blocks)
      // AI 프롬프트 저장 (코드 생성 시 지식베이스 참조용)
      setPendingPrompt(`${previewData.taskName} - ${previewData.summary}`)
      setNewWorkspaceName(previewData.taskName || "새 자동화")
      setShowPreview(false)
      setShowNewWorkspaceDialog(true)
    } catch (error) {
      console.error("블록 생성 오류:", error)
    }
  }

  const handleCreateNewWorkspace = () => {
    if (pendingBlocks && newWorkspaceName.trim()) {
      // 새 워크스페이스로 블록 추가 (AI 프롬프트 포함)
      multiWorkspaceHandleRef.current?.addWorkspaceFromPurchase(newWorkspaceName.trim(), pendingBlocks, pendingPrompt || undefined)
      setPendingBlocks(null)
      setPendingPrompt("")
      setNewWorkspaceName("")
      setShowNewWorkspaceDialog(false)
      setView("builder")
    }
  }

  // 대화형 AI에서 생성된 워크플로우 처리 → 프리뷰 모달 표시
  const handleConversationWorkflow = (workflow: any) => {
    console.log("[AI] 워크플로우 수신 - 프리뷰 표시:", workflow)

    try {
      // workflow를 AIPreviewData 형식으로 변환
      const groups = (workflow.groups || []).map((group: any) => ({
        id: group.id,
        label: group.label,
        description: group.description || "",
        color: group.color || "#3b82f6",
        steps: (group.steps || []).map((step: any) => ({
          id: step.id,
          label: step.label,
          description: step.description || "",
          blockType: step.block_type,
          color: step.color || group.color || "#3b82f6",
          fieldValues: step.field_values || {},
        })),
      }))

      // 프리뷰 데이터 설정
      setPreviewData({
        taskName: workflow.task_name || "AI 자동화",
        summary: workflow.summary || "",
        confidence: workflow.confidence || 80,
        groups: groups,
      })

      // 스트리밍 효과로 프리뷰 표시
      setStreamingGroups([])
      setStreamingInfo({
        taskName: workflow.task_name || "AI 자동화",
        summary: workflow.summary || "",
        confidence: workflow.confidence || 80,
        totalGroups: groups.length,
      })
      setIsStreaming(true)
      setShowPreview(true)

      // 0.5초 간격으로 그룹을 하나씩 추가
      groups.forEach((group: any, index: number) => {
        setTimeout(() => {
          setStreamingGroups((prev) => [...prev, group])

          // 마지막 그룹이면 스트리밍 종료
          if (index === groups.length - 1) {
            setTimeout(() => {
              setIsStreaming(false)
            }, 300)
          }
        }, (index + 1) * 500)
      })
    } catch (error) {
      console.error("[AI] 워크플로우 프리뷰 오류:", error)
      // 오류 시 기본 프리뷰 표시
      setPreviewData({
        taskName: workflow.task_name || "AI 자동화",
        summary: "워크플로우를 생성했습니다.",
        confidence: 50,
        groups: [{
          id: "g1",
          label: "시작",
          description: "워크플로우 시작",
          color: "#22c55e",
          steps: [{
            id: "s1",
            label: "시작",
            description: "시작 블록",
            blockType: "start",
            color: "#22c55e",
            fieldValues: {},
          }],
        }],
      })
      setShowPreview(true)
    }
  }

  const handleSell = useCallback(() => {
    setShowSellModal(true)
  }, [])

  // Only access user after all hooks are called, and render guard at the end
  // Show loading state while checking authentication to prevent flash of login page
  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-foreground flex items-center justify-center animate-pulse">
            <span className="text-xl font-bold text-background">A</span>
          </div>
          <p className="text-sm text-muted-foreground">로딩 중...</p>
        </div>
      </div>
    )
  }

  if (!user) return <AuthPage />

  const chatUnread = unreadCount(user.id)
  const NAV_ITEMS = [
    { id: "builder" as View, label: "빌더", icon: Wrench },
    { id: "marketplace" as View, label: "마켓플레이스", icon: Store },
    { id: "mypage" as View, label: "마이페이지", icon: User },
    { id: "chat" as View, label: "채팅", icon: MessageSquare, ...(chatUnread > 0 ? { badge: chatUnread } : {}) },
  ]

  const activeNavId = view === "market-detail" ? "marketplace" : view

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 flex-shrink-0">
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-2xl bg-foreground flex items-center justify-center">
              <span className="text-base font-bold text-background">A</span>
            </div>
            <span className="text-base font-bold text-foreground">AutoFlow</span>
          </div>
          <div className="flex items-center gap-1 bg-secondary rounded-2xl p-1">
            {NAV_ITEMS.map(({ id, label, icon: Icon, badge }) => (
              <button
                key={id}
                onClick={() => setView(id)}
                className={`relative flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-sm font-medium transition-all ${
                  activeNavId === id
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
                {badge && badge > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-foreground text-background text-[9px] font-bold flex items-center justify-center">
                    {badge > 9 ? "9+" : badge}
                  </span>
                )}
              </button>
            ))}
          </div>
          {/* User info + logout */}
          <div className="flex items-center gap-2">
            <div className="text-right hidden sm:block">
              <p className="text-xs font-semibold leading-none">{user.name}</p>
            </div>
            <button
              onClick={logout}
              className="w-8 h-8 rounded-xl hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
              title="로그아웃"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {view === "builder" && (
          <MultiWorkspace
            key={generatedBlocks ? JSON.stringify(generatedBlocks.map((b) => b.instanceId)) : "default"}
            isConnected={isConnected}
            onConnect={() => setIsConnected(true)}
            onWorkspacesChange={handleWorkspacesChange}
            initialBlocks={generatedBlocks}
            handleRef={multiWorkspaceHandleRef}
            onOpenAI={() => setShowCreateDialog(true)}
            onOpenVideo={() => setShowVideoModal(true)}
          />
        )}
        {view === "marketplace" && (
          <div className="flex-1 overflow-hidden">
            <MarketplacePage onPurchase={handleMarketImport} onCardClick={handleMarketItemClick} onSell={handleSell} />
          </div>
        )}
        {view === "market-detail" && selectedMarketItem && (
          <div className="flex-1 overflow-hidden">
            <MarketplaceDetailPage
              item={selectedMarketItem}
              onBack={() => setView("marketplace")}
              onPurchase={(item, blocksData) => { handleMarketImport(item, blocksData); setView("builder") }}
            />
          </div>
        )}
        {view === "mypage" && (
          <div className="flex-1 overflow-hidden">
            <MyPage
              onAddToWorkspace={(purchase, sheetName) => {
                multiWorkspaceHandleRef.current?.addWorkspaceFromPurchase(sheetName)
                setView("builder")
              }}
            />
          </div>
        )}
        {view === "chat" && (
          <div className="flex-1 overflow-hidden">
            <ChatPage />
          </div>
        )}
      </div>

      {/* Modals */}
      {/* AI 다이얼로그 (대화형 통합) */}
      <AICreateDialog
        isOpen={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onAnalyze={handleAIAnalyze}
        onWorkflowGenerated={handleConversationWorkflow}
        isAnalyzing={isAnalyzing}
      />
      <AIPreviewModal
        isOpen={showPreview}
        onClose={() => {
          setShowPreview(false)
          if (abortStreamRef.current) {
            abortStreamRef.current()
            abortStreamRef.current = null
          }
          setIsStreaming(false)
          setIsAnalyzing(false)
        }}
        onGenerate={handleGenerateBlocks}
        data={previewData}
        isStreaming={isStreaming}
        streamingInfo={streamingInfo}
        streamingGroups={streamingGroups}
      />
      {showSellModal && (
        <SellModal
          onClose={() => setShowSellModal(false)}
          workspaces={workspacesRef.current}
        />
      )}
      <VideoUploadModal
        isOpen={showVideoModal}
        onClose={() => setShowVideoModal(false)}
        onComplete={(blocks) => {
          const workspaceBlocks: WorkspaceBlock[] = blocks.map((b) => {
            const def = BLOCK_DEFINITIONS.find((d) => d.id === b.id)
            return {
              id: def?.id || b.id,
              type: def?.type || b.type,
              category: (def?.category || b.category) as any,
              label: def?.label || b.label,
              icon: def?.icon || b.icon,
              color: def?.color || b.color,
              fields: def?.fields || [], // Ensure fields are always included
              instanceId: b.instance_id,
              fieldValues: b.field_values || {},
              groupId: b.group_id,
              groupLabel: b.group_label,
              groupColor: b.group_color,
            } as WorkspaceBlock
          })
          // 영상 분석도 새 워크스페이스로 생성
          setPendingBlocks(workspaceBlocks)
          setPendingPrompt("영상 분석 자동화")  // 영상 기반 프롬프트
          setNewWorkspaceName("영상 분석 자동화")
          setShowVideoModal(false)
          setShowNewWorkspaceDialog(true)
        }}
        onWorkflowReady={(workflow) => {
          // 영상 분석 결과를 AI 프롬프트처럼 스트리밍 효과로 표시
          setShowVideoModal(false)
          setStreamingGroups([])
          setStreamingInfo({
            taskName: workflow.taskName,
            summary: workflow.summary,
            confidence: workflow.confidence,
            totalGroups: workflow.groups.length,
          })
          setIsStreaming(true)
          setShowPreview(true)

          // 1초 간격으로 그룹을 하나씩 추가
          workflow.groups.forEach((group, index) => {
            setTimeout(() => {
              setStreamingGroups((prev) => [...prev, group])

              // 마지막 그룹이면 스트리밍 종료
              if (index === workflow.groups.length - 1) {
                setTimeout(() => {
                  setIsStreaming(false)
                  setPreviewData({
                    taskName: workflow.taskName,
                    summary: workflow.summary,
                    confidence: workflow.confidence,
                    groups: workflow.groups,
                  })
                }, 500)
              }
            }, (index + 1) * 1000) // 1초 간격
          })
        }}
      />

      {/* 새 워크스페이스 이름 입력 다이얼로그 (컴팩트) */}
      <Dialog open={showNewWorkspaceDialog} onOpenChange={setShowNewWorkspaceDialog}>
        <DialogContent className="sm:max-w-sm rounded-2xl p-5">
          <DialogHeader className="pb-2">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                <Plus className="w-4 h-4 text-primary" />
              </div>
              <DialogTitle className="text-sm font-semibold">워크스페이스 이름</DialogTitle>
            </div>
          </DialogHeader>
          <div className="py-2">
            <Input
              value={newWorkspaceName}
              onChange={(e) => setNewWorkspaceName(e.target.value)}
              placeholder="예: 네이버 뉴스 크롤링"
              className="rounded-xl h-10 text-sm"
              onKeyDown={(e) => {
                if (e.key === "Enter" && newWorkspaceName.trim()) {
                  handleCreateNewWorkspace()
                }
              }}
              autoFocus
            />
          </div>
          <DialogFooter className="gap-2 pt-1">
            <Button
              variant="ghost"
              size="sm"
              className="rounded-xl"
              onClick={() => {
                setShowNewWorkspaceDialog(false)
                setPendingBlocks(null)
              }}
            >
              취소
            </Button>
            <Button
              size="sm"
              className="rounded-xl px-4"
              onClick={handleCreateNewWorkspace}
              disabled={!newWorkspaceName.trim()}
            >
              생성
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
