"use client"

import { useState, useCallback, useRef, useEffect } from "react"
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
  type DragOverEvent,
} from "@dnd-kit/core"
import { arrayMove, sortableKeyboardCoordinates } from "@dnd-kit/sortable"
import { BlockPalette } from "@/components/blocks/block-palette"
import { WorkspaceCanvas } from "@/components/blocks/workspace-canvas"
import { ExecutionPanel } from "@/components/blocks/execution-panel"
import { DraggableBlock } from "@/components/blocks/draggable-block"
import { VariablesPanel } from "@/components/blocks/variables-panel"
import { Plus, X, Pencil, Check, AlertTriangle, Loader2, Video, Play, Square } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import {
  BLOCK_DEFINITIONS,
  type BlockDefinition,
  type WorkspaceBlock,
} from "@/types/blocks"
import { api, type WorkspaceResponse } from "@/lib/api"
import { useAuth } from "@/contexts/auth-context"

interface Workspace {
  id: string
  name: string
  blocks: WorkspaceBlock[]
  isNew?: boolean
  prompt?: string  // AI 생성 시 원본 프롬프트 (지식베이스 참조용)
}

function apiWorkspaceToLocal(ws: WorkspaceResponse): Workspace {
  return {
    id: ws.id,
    name: ws.name,
    blocks: (ws.blocks_data || []).map((b: any) => {
      // Find the block definition to get the fields
      const def = BLOCK_DEFINITIONS.find((d) => d.id === b.id)
      return {
        ...b,
        // Merge fields from definition (fields are not stored in DB)
        fields: def?.fields || [],
        instanceId: b.instanceId || b.instance_id,
        fieldValues: b.fieldValues || b.field_values || {},
      }
    }),
  }
}

function localBlocksToApi(blocks: WorkspaceBlock[]): any[] {
  return blocks.map((b) => ({
    id: b.id,
    type: b.type,
    category: b.category,
    label: b.label,
    icon: b.icon,
    color: b.color,
    instanceId: b.instanceId,
    fieldValues: b.fieldValues,
    groupId: b.groupId,
    groupLabel: b.groupLabel,
    groupColor: b.groupColor,
  }))
}

export interface MultiWorkspaceHandle {
  addWorkspaceFromPurchase: (name: string, blocks?: WorkspaceBlock[], prompt?: string) => void
}

interface MultiWorkspaceProps {
  isConnected: boolean
  onConnect: () => void
  initialBlocks?: WorkspaceBlock[] | null
  initialPrompt?: string | null  // AI 생성 시 원본 프롬프트
  onInitialBlocksConsumed?: () => void
  onWorkspacesChange?: (ws: { id: string; name: string; blocks: WorkspaceBlock[] }[]) => void
  handleRef?: React.MutableRefObject<MultiWorkspaceHandle | null>
  onOpenAI?: () => void
  onOpenVideo?: () => void
}

export function MultiWorkspace({ isConnected, onConnect, initialBlocks, initialPrompt, onInitialBlocksConsumed, onWorkspacesChange, handleRef, onOpenAI, onOpenVideo }: MultiWorkspaceProps) {
  const { user } = useAuth()
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [activeWsId, setActiveWsId] = useState<string>("")
  const [activeBlock, setActiveBlock] = useState<BlockDefinition | null>(null)
  const [dragLeftPalette, setDragLeftPalette] = useState(false)
  const [editingTabId, setEditingTabId] = useState<string | null>(null)
  const [editingName, setEditingName] = useState("")
  const [deleteStep, setDeleteStep] = useState<{ id: string; step: 1 | 2 } | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [workspaceVariables, setWorkspaceVariables] = useState<Record<string, Record<string, string>>>({})
  const editInputRef = useRef<HTMLInputElement>(null)
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // 현재 워크스페이스의 변수
  const currentVariables = workspaceVariables[activeWsId] || {}
  const setCurrentVariables = (vars: Record<string, string>) => {
    setWorkspaceVariables((prev) => ({ ...prev, [activeWsId]: vars }))
  }

  const activeWs = workspaces.find((w) => w.id === activeWsId) ?? workspaces[0]

  // Load workspaces from API
  useEffect(() => {
    if (!user) return
    const loadWorkspaces = async () => {
      setIsLoading(true)
      try {
        const response = await api.getWorkspaces()
        if (response.workspaces.length > 0) {
          const loaded = response.workspaces.map(apiWorkspaceToLocal)
          setWorkspaces(loaded)
          setActiveWsId(loaded[0].id)
        } else {
          const newWs = await api.createWorkspace({ name: "작업 1" })
          const local = apiWorkspaceToLocal(newWs)
          setWorkspaces([local])
          setActiveWsId(local.id)
        }
      } catch {
        const localWs: Workspace = { id: `ws-${Date.now()}`, name: "작업 1", blocks: [], isNew: true }
        setWorkspaces([localWs])
        setActiveWsId(localWs.id)
      } finally {
        setIsLoading(false)
      }
    }
    loadWorkspaces()
  }, [user])

  // Apply initial blocks when provided (from AI generation)
  useEffect(() => {
    if (initialBlocks && initialBlocks.length > 0 && workspaces.length > 0 && activeWsId) {
      setWorkspaces((prev) => {
        const updated = prev.map((w) =>
          w.id === activeWsId ? { ...w, blocks: initialBlocks } : w
        )
        onWorkspacesChange?.(updated)
        return updated
      })
      onInitialBlocksConsumed?.()
      // Save to API
      api.updateWorkspace(activeWsId, { blocks_data: localBlocksToApi(initialBlocks) }).catch(() => {})
    }
  }, [initialBlocks, activeWsId, workspaces.length, onWorkspacesChange, onInitialBlocksConsumed])

  // Notify parent with workspace list
  useEffect(() => {
    if (workspaces.length > 0) {
      onWorkspacesChange?.(workspaces)
    }
  }, [workspaces, onWorkspacesChange])

  useEffect(() => {
    if (editingTabId && editInputRef.current) {
      editInputRef.current.focus()
      editInputRef.current.select()
    }
  }, [editingTabId])

  const setBlocks = useCallback((wsId: string, updater: (prev: WorkspaceBlock[]) => WorkspaceBlock[]) => {
    setWorkspaces((prev) => {
      const next = prev.map((w) => (w.id === wsId ? { ...w, blocks: updater(w.blocks) } : w))
      onWorkspacesChange?.(next)

      // Debounced save to API
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
      saveTimeoutRef.current = setTimeout(async () => {
        const ws = next.find((w) => w.id === wsId)
        if (ws && !ws.isNew) {
          setIsSaving(true)
          try {
            await api.updateWorkspace(wsId, { blocks_data: localBlocksToApi(ws.blocks) })
          } catch {
            // Silently fail
          } finally {
            setIsSaving(false)
          }
        }
      }, 1000)

      return next
    })
  }, [onWorkspacesChange])

  const addWorkspace = async () => {
    try {
      const newWs = await api.createWorkspace({ name: `작업 ${workspaces.length + 1}` })
      const local = apiWorkspaceToLocal(newWs)
      setWorkspaces((prev) => {
        const next = [...prev, local]
        onWorkspacesChange?.(next)
        return next
      })
      setActiveWsId(local.id)
    } catch {
      const ws: Workspace = { id: `ws-${Date.now()}`, name: `작업 ${workspaces.length + 1}`, blocks: [], isNew: true }
      setWorkspaces((prev) => {
        const next = [...prev, ws]
        onWorkspacesChange?.(next)
        return next
      })
      setActiveWsId(ws.id)
    }
  }

  const addWorkspaceFromPurchase = useCallback(async (name: string, blocks: WorkspaceBlock[] = [], prompt?: string) => {
    try {
      const newWs = await api.createWorkspace({ name, blocks_data: localBlocksToApi(blocks) })
      const local = apiWorkspaceToLocal(newWs)
      local.blocks = blocks
      local.prompt = prompt  // AI 생성 시 원본 프롬프트 저장
      setWorkspaces((prev) => {
        const next = [...prev, local]
        onWorkspacesChange?.(next)
        return next
      })
      setActiveWsId(local.id)
    } catch {
      const ws: Workspace = { id: `ws-${Date.now()}`, name, blocks, isNew: true, prompt }
      setWorkspaces((prev) => {
        const next = [...prev, ws]
        onWorkspacesChange?.(next)
        return next
      })
      setActiveWsId(ws.id)
    }
  }, [onWorkspacesChange])

  // Expose imperative handle to parent
  useEffect(() => {
    if (handleRef) handleRef.current = { addWorkspaceFromPurchase }
  }, [handleRef, addWorkspaceFromPurchase])

  const requestDeleteWorkspace = (id: string) => {
    if (workspaces.length === 1) return
    setDeleteStep({ id, step: 1 })
  }

  const proceedToStep2 = () => {
    if (deleteStep) setDeleteStep({ ...deleteStep, step: 2 })
  }

  const confirmFinalDelete = async () => {
    if (!deleteStep) return
    const id = deleteStep.id
    const idx = workspaces.findIndex((w) => w.id === id)
    const next = workspaces[idx === 0 ? 1 : idx - 1]
    const ws = workspaces.find((w) => w.id === id)

    setWorkspaces((prev) => {
      const filtered = prev.filter((w) => w.id !== id)
      onWorkspacesChange?.(filtered)
      return filtered
    })
    if (activeWsId === id) setActiveWsId(next.id)
    setDeleteStep(null)

    // Delete from API
    if (ws && !ws.isNew) {
      try {
        await api.deleteWorkspace(id)
      } catch {
        // Silently fail
      }
    }
  }

  const cancelDelete = () => setDeleteStep(null)

  const startEditTab = (ws: Workspace) => {
    setEditingTabId(ws.id)
    setEditingName(ws.name)
  }

  const commitEditTab = async () => {
    if (!editingTabId) return
    const newName = editingName.trim()
    const ws = workspaces.find((w) => w.id === editingTabId)

    setWorkspaces((prev) => {
      const next = prev.map((w) => (w.id === editingTabId ? { ...w, name: newName || w.name } : w))
      onWorkspacesChange?.(next)
      return next
    })
    setEditingTabId(null)

    // Save to API
    if (ws && !ws.isNew && newName) {
      try {
        await api.updateWorkspace(editingTabId, { name: newName })
      } catch {
        // Silently fail
      }
    }
  }

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 3 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  const handleDragStart = (event: DragStartEvent) => {
    const blockId = String(event.active.id).replace("palette-", "")
    const block = BLOCK_DEFINITIONS.find((b) => b.id === blockId)
    if (block) { setActiveBlock(block); setDragLeftPalette(false) }
  }

  const handleDragOver = (event: DragOverEvent) => {
    if (!String(event.active.id).startsWith("palette-")) return
    if (event.over ? String(event.over.id) !== "palette-container" : true) setDragLeftPalette(true)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    setActiveBlock(null)
    setDragLeftPalette(false)
    const activeId = String(active.id)

    if (activeId.startsWith("palette-")) {
      const overId = over ? String(over.id) : null
      if (overId !== "palette-container" && dragLeftPalette) {
        const blockId = activeId.replace("palette-", "")
        const blockDef = BLOCK_DEFINITIONS.find((b) => b.id === blockId)
        if (blockDef) {
          setBlocks(activeWsId, (prev) => [
            ...prev,
            { ...blockDef, instanceId: `${blockDef.id}-${Date.now()}`, fieldValues: {} },
          ])
        }
      }
      return
    }

    if (!over) return
    const overId = String(over.id)
    if (!overId.startsWith("palette-")) {
      const blocks = activeWs.blocks
      const oldIdx = blocks.findIndex((b) => b.instanceId === activeId)
      const newIdx = blocks.findIndex((b) => b.instanceId === overId)
      if (oldIdx !== -1 && newIdx !== -1 && oldIdx !== newIdx) {
        setBlocks(activeWsId, (prev) => arrayMove(prev, oldIdx, newIdx))
      }
    }
  }

  const handleUpdateBlock = useCallback((instanceId: string, fieldValues: Record<string, string | number>) => {
    setBlocks(activeWsId, (prev) => prev.map((b) => b.instanceId === instanceId ? { ...b, fieldValues } : b))
  }, [activeWsId, setBlocks])

  const handleDeleteBlock = useCallback((instanceId: string) => {
    setBlocks(activeWsId, (prev) => prev.filter((b) => b.instanceId !== instanceId))
  }, [activeWsId, setBlocks])

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">워크스페이스 불러오는 중...</p>
        </div>
      </div>
    )
  }

  return (
    <DndContext
      id="autoflow-builder-dnd"
      sensors={sensors}
      accessibility={{
        announcements: {
          onDragStart: () => "",
          onDragOver: () => "",
          onDragEnd: () => "",
          onDragCancel: () => "",
        },
        screenReaderInstructions: { draggable: "" },
      }}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Workspace tabs */}
        <div className="flex items-center gap-0 border-b bg-muted/30 px-4 flex-shrink-0 overflow-x-auto">
          {workspaces.map((ws) => (
            <div
              key={ws.id}
              className={`group flex items-center gap-1.5 px-3 py-2 border-b-2 text-sm cursor-pointer flex-shrink-0 transition-colors ${
                ws.id === activeWsId
                  ? "border-primary text-foreground font-medium"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => setActiveWsId(ws.id)}
            >
              {editingTabId === ws.id ? (
                <input
                  ref={editInputRef}
                  value={editingName}
                  onChange={(e) => setEditingName(e.target.value)}
                  onBlur={commitEditTab}
                  onKeyDown={(e) => { if (e.key === "Enter") commitEditTab() }}
                  className="w-24 bg-transparent border-none outline-none text-sm font-medium"
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <span className="max-w-[120px] truncate">{ws.name}</span>
              )}
              <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                {editingTabId === ws.id ? (
                  <button
                    onClick={(e) => { e.stopPropagation(); commitEditTab() }}
                    className="p-0.5 hover:text-primary"
                  >
                    <Check className="w-3 h-3" />
                  </button>
                ) : (
                  <button
                    onClick={(e) => { e.stopPropagation(); startEditTab(ws) }}
                    className="p-0.5 hover:text-foreground"
                  >
                    <Pencil className="w-3 h-3" />
                  </button>
                )}
                {workspaces.length > 1 && (
                  <button
                    onClick={(e) => { e.stopPropagation(); requestDeleteWorkspace(ws.id) }}
                    className="p-0.5 hover:text-destructive"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
              {ws.id === activeWsId && (
                <span className="ml-1 text-xs text-muted-foreground">
                  {ws.blocks.length}블록
                </span>
              )}
            </div>
          ))}
          <button
            onClick={addWorkspace}
            className="flex items-center gap-1 px-3 py-2 text-muted-foreground hover:text-foreground text-sm flex-shrink-0 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>추가</span>
          </button>

          <div className="ml-auto flex items-center gap-2 pr-3 flex-shrink-0">
            {isSaving && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin" />
                저장 중...
              </span>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={onOpenVideo}
              className="rounded-xl h-7 px-3 text-xs font-semibold gap-1.5"
            >
              <Video className="w-3.5 h-3.5" />
              영상 분석
            </Button>
            <Button
              size="sm"
              onClick={onOpenAI}
              className="rounded-xl h-7 px-3 text-xs font-semibold"
            >
              AI 블록 자동화 생성
            </Button>
          </div>
        </div>

        {/* Three-column layout */}
        <div className="flex-1 flex overflow-hidden">
          <aside className="w-64 border-r bg-muted/30 flex-shrink-0 flex flex-col">
            <div className="flex-1 overflow-y-auto">
              <BlockPalette />
            </div>
          </aside>
          <main className="flex-1 overflow-hidden">
            <WorkspaceCanvas
              key={activeWsId}
              blocks={activeWs.blocks}
              onUpdateBlock={handleUpdateBlock}
              onDeleteBlock={handleDeleteBlock}
            />
          </main>
          <aside className="w-72 border-l bg-muted/30 flex-shrink-0">
            <ExecutionPanel
              isConnected={isConnected}
              onConnect={onConnect}
              blocks={activeWs.blocks}
              workspaceName={activeWs.name}
              variables={currentVariables}
              prompt={activeWs.prompt}
            />
          </aside>
        </div>
      </div>

      <DragOverlay>
        {activeBlock && (
          <div style={{ backgroundColor: activeBlock.color }} className="rounded-2xl opacity-90">
            <DraggableBlock block={activeBlock} isPalette={false} />
          </div>
        )}
      </DragOverlay>

      {/* Step 1 dialog */}
      <Dialog open={deleteStep?.step === 1} onOpenChange={(o) => !o && cancelDelete()}>
        <DialogContent className="max-w-sm rounded-2xl">
          <DialogHeader>
            <div className="flex items-center gap-3 mb-1">
              <div className="w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-destructive" />
              </div>
              <DialogTitle className="text-base">작업을 삭제할까요?</DialogTitle>
            </div>
            <DialogDescription className="text-sm leading-relaxed pl-[52px]">
              &quot;{workspaces.find((w) => w.id === deleteStep?.id)?.name}&quot; 작업과 안에 있는 모든 블록이 삭제됩니다.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 mt-2">
            <Button variant="outline" className="rounded-xl" onClick={cancelDelete}>취소</Button>
            <Button variant="destructive" className="rounded-xl" onClick={proceedToStep2}>계속</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Step 2 dialog */}
      <Dialog open={deleteStep?.step === 2} onOpenChange={(o) => !o && cancelDelete()}>
        <DialogContent className="max-w-sm rounded-2xl">
          <DialogHeader>
            <div className="flex items-center gap-3 mb-1">
              <div className="w-10 h-10 rounded-full bg-destructive/20 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-destructive" />
              </div>
              <DialogTitle className="text-base text-destructive">정말 삭제하시겠습니까?</DialogTitle>
            </div>
            <DialogDescription className="text-sm leading-relaxed pl-[52px]">
              이 작업은 <strong>복구할 수 없습니다.</strong> 삭제된 작업과 블록은 영구적으로 사라집니다.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 mt-2">
            <Button variant="outline" className="rounded-xl" onClick={cancelDelete}>취소</Button>
            <Button variant="destructive" className="rounded-xl font-bold" onClick={confirmFinalDelete}>영구 삭제</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </DndContext>
  )
}
