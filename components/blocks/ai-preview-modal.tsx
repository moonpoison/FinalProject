"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronUp, ArrowRight, CheckCircle2, Gauge, Layers, Info, Loader2 } from "lucide-react"

// ── Types ─────────────────────────────────────────────────────────────────────

export interface WorkflowStep {
  id: string
  label: string        // e.g. "로그인 페이지 열기"
  description: string  // e.g. "Chrome에서 네이버 로그인 URL을 엽니다"
  blockType: string    // block id to generate
  color: string
  icon?: string
  fieldValues?: Record<string, any>  // 자동으로 채워질 필드 값
}

export interface WorkflowGroup {
  id: string
  label: string        // e.g. "로그인"
  description: string  // e.g. "네이버 계정으로 자동 로그인합니다"
  color: string
  steps: WorkflowStep[]
}

export interface AIPreviewData {
  taskName: string
  summary: string
  groups: WorkflowGroup[]
  confidence: number
}

interface AIPreviewModalProps {
  isOpen: boolean
  onClose: () => void
  onGenerate: () => void
  data: AIPreviewData
  isStreaming?: boolean
  streamingInfo?: { taskName: string; summary: string; confidence: number; totalGroups: number } | null
  streamingGroups?: WorkflowGroup[]
}

// ── Sub-components ────────────────────────────────────────────────────────────

function GroupCard({ group, index, isLast, isNew }: { group: WorkflowGroup; index: number; isLast: boolean; isNew?: boolean }) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className={`relative transition-all duration-500 ${isNew ? "animate-in fade-in slide-in-from-bottom-4" : ""}`}>
      {/* Vertical connector to next group */}
      {!isLast && (
        <div className="absolute left-[22px] top-full w-0.5 h-4 z-10" style={{ backgroundColor: group.color + "60" }} />
      )}

      <div className="rounded-2xl border-2 overflow-hidden" style={{ borderColor: group.color + "40" }}>
        {/* Group header */}
        <button
          className="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors hover:opacity-90"
          style={{ backgroundColor: group.color + "18" }}
          onClick={() => setExpanded((v) => !v)}
        >
          {/* Group number dot */}
          <div
            className="w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-bold flex-shrink-0 shadow-sm"
            style={{ backgroundColor: group.color }}
          >
            {index + 1}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm text-foreground">{group.label}</span>
              <span
                className="text-[10px] font-semibold px-2 py-0.5 rounded-full text-white"
                style={{ backgroundColor: group.color }}
              >
                {group.steps.length}단계
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5 truncate">{group.description}</p>
          </div>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          ) : (
            <ChevronDown className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          )}
        </button>

        {/* Expanded steps */}
        {expanded && (
          <div className="px-4 py-3 space-y-2 bg-background">
            {group.steps.map((step, si) => (
              <div key={step.id} className="flex items-start gap-3">
                {/* Step connector */}
                <div className="flex flex-col items-center flex-shrink-0 mt-0.5">
                  <div
                    className="w-5 h-5 rounded-full border-2 flex items-center justify-center text-[10px] font-bold"
                    style={{ borderColor: group.color, color: group.color }}
                  >
                    {si + 1}
                  </div>
                  {si < group.steps.length - 1 && (
                    <div className="w-0.5 h-4 mt-0.5" style={{ backgroundColor: group.color + "40" }} />
                  )}
                </div>
                <div className="flex-1 pb-1">
                  <p className="text-xs font-semibold text-foreground">{step.label}</p>
                  <p className="text-[11px] text-muted-foreground leading-relaxed mt-0.5">{step.description}</p>
                </div>
              </div>
            ))}
            {/* Block flow preview */}
            <div className="mt-3 pt-3 border-t border-border/50">
              <p className="text-[10px] text-muted-foreground font-medium mb-2 flex items-center gap-1">
                <Layers className="w-3 h-3" /> 생성될 블록
              </p>
              <div className="flex items-center gap-1.5 flex-wrap">
                {group.steps.map((step, si) => (
                  <div key={step.id} className="flex items-center gap-1.5">
                    <span
                      className="text-[10px] font-semibold px-2 py-1 rounded-lg text-white"
                      style={{ backgroundColor: step.color }}
                    >
                      {step.label}
                    </span>
                    {si < group.steps.length - 1 && (
                      <ArrowRight className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Placeholder for groups that are still loading
function GroupPlaceholder({ index }: { index: number }) {
  return (
    <div className="relative animate-pulse">
      <div className="rounded-2xl border-2 border-muted/40 overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-3 bg-muted/20">
          <div className="w-9 h-9 rounded-full bg-muted flex items-center justify-center">
            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
          </div>
          <div className="flex-1">
            <div className="h-4 w-24 bg-muted rounded mb-1" />
            <div className="h-3 w-40 bg-muted/60 rounded" />
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Main Modal ────────────────────────────────────────────────────────────────

export function AIPreviewModal({ isOpen, onClose, onGenerate, data, isStreaming, streamingInfo, streamingGroups }: AIPreviewModalProps) {
  const [newGroupIndex, setNewGroupIndex] = useState<number | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const lastGroupRef = useRef<HTMLDivElement>(null)

  // Track new groups for animation and auto-scroll
  useEffect(() => {
    if (streamingGroups && streamingGroups.length > 0) {
      setNewGroupIndex(streamingGroups.length - 1)
      const timer = setTimeout(() => setNewGroupIndex(null), 600)

      // Auto-scroll to the new group
      setTimeout(() => {
        lastGroupRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })
      }, 100)

      return () => clearTimeout(timer)
    }
  }, [streamingGroups?.length])

  if (!isOpen) return null

  // Use streaming data if available, otherwise use final data
  const displayGroups = isStreaming && streamingGroups ? streamingGroups : data.groups
  const displayInfo = isStreaming && streamingInfo ? streamingInfo : { taskName: data.taskName, summary: data.summary, confidence: data.confidence, totalGroups: data.groups.length }
  const remainingPlaceholders = isStreaming && streamingInfo ? Math.max(0, streamingInfo.totalGroups - (streamingGroups?.length || 0)) : 0

  const totalSteps = displayGroups.reduce((s, g) => s + g.steps.length, 0)
  const confColor = displayInfo.confidence >= 80 ? "#22c55e" : displayInfo.confidence >= 60 ? "#eab308" : "#ef4444"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="relative bg-background rounded-3xl shadow-2xl w-full max-w-lg mx-4 flex flex-col max-h-[90vh] overflow-hidden">

        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b flex-shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-base text-foreground">AI 워크플로우 분석 결과</h2>
              {isStreaming && (
                <span className="flex items-center gap-1.5 text-xs text-primary font-medium">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  생성 중...
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground mt-0.5 leading-relaxed">
              {displayInfo.summary || "워크플로우를 분석하고 있습니다..."}
            </p>
          </div>

          {/* Stats row */}
          <div className="flex items-center gap-3 mt-4">
            <div className="flex-1 bg-secondary rounded-xl px-3 py-2 text-center">
              <p className="text-xs text-muted-foreground">작업 그룹</p>
              <p className="text-lg font-bold text-foreground">
                {isStreaming ? (
                  <span className="flex items-center justify-center gap-1">
                    {streamingGroups?.length || 0}
                    <span className="text-xs text-muted-foreground font-normal">/ {streamingInfo?.totalGroups || "?"}</span>
                  </span>
                ) : (
                  displayGroups.length
                )}
              </p>
            </div>
            <div className="flex-1 bg-secondary rounded-xl px-3 py-2 text-center">
              <p className="text-xs text-muted-foreground">전체 단계</p>
              <p className="text-lg font-bold text-foreground">{totalSteps}</p>
            </div>
            <div className="flex-1 bg-secondary rounded-xl px-3 py-2 text-center">
              <p className="text-xs text-muted-foreground">AI 정확도</p>
              <p className="text-lg font-bold" style={{ color: confColor }}>{displayInfo.confidence}%</p>
            </div>
          </div>
        </div>

        {/* Timeline body */}
        <div ref={scrollContainerRef} className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
          {/* Flow summary chips */}
          {displayGroups.length > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap mb-1">
              {displayGroups.map((g, i) => (
                <div key={g.id} className="flex items-center gap-1.5">
                  <span
                    className="text-xs font-semibold px-3 py-1 rounded-full text-white shadow-sm transition-all duration-300"
                    style={{ backgroundColor: g.color }}
                  >
                    {g.label}
                  </span>
                  {i < displayGroups.length - 1 && (
                    <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />
                  )}
                </div>
              ))}
              {isStreaming && remainingPlaceholders > 0 && (
                <>
                  <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />
                  <span className="text-xs font-semibold px-3 py-1 rounded-full bg-muted text-muted-foreground animate-pulse">
                    ...
                  </span>
                </>
              )}
            </div>
          )}

          <div className="space-y-3">
            {displayGroups.map((group, i) => (
              <div key={group.id} ref={i === displayGroups.length - 1 ? lastGroupRef : undefined}>
                <GroupCard
                  group={group}
                  index={i}
                  isLast={i === displayGroups.length - 1 && remainingPlaceholders === 0}
                  isNew={newGroupIndex === i}
                />
              </div>
            ))}
            {/* Placeholders for remaining groups */}
            {isStreaming && Array.from({ length: remainingPlaceholders }).map((_, i) => (
              <GroupPlaceholder key={`placeholder-${i}`} index={displayGroups.length + i} />
            ))}
          </div>

          {/* Confidence bar */}
          {!isStreaming && displayGroups.length > 0 && (
            <div className="pt-2">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <Gauge className="w-3.5 h-3.5" />
                  분석 정확도
                </span>
                <span className="text-xs font-bold" style={{ color: confColor }}>{displayInfo.confidence}%</span>
              </div>
              <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${displayInfo.confidence}%`, backgroundColor: confColor }}
                />
              </div>
              {displayInfo.confidence < 75 && (
                <p className="text-[11px] text-muted-foreground mt-1.5 flex items-center gap-1">
                  <Info className="w-3 h-3" />
                  정확도가 낮을 수 있습니다. 생성 후 블록을 직접 조정해 주세요.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t flex gap-3 flex-shrink-0">
          <Button variant="outline" onClick={onClose} className="flex-1 rounded-2xl h-11">
            취소
          </Button>
          <Button
            onClick={onGenerate}
            disabled={isStreaming || displayGroups.length === 0}
            className="flex-1 rounded-2xl h-11 font-semibold gap-2"
          >
            {isStreaming ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                분석 중...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                승인하고 블록 생성
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
