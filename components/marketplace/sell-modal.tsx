"use client"

import { useState } from "react"
import { X, Plus, Minus, BadgeCheck, Info, Layers, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/lib/api"
import type { MarketCategory } from "@/data/marketplace"
import type { WorkspaceBlock } from "@/types/blocks"

interface WorkspaceOption {
  id: string
  name: string
  blocks: WorkspaceBlock[]
}

interface SellModalProps {
  onClose: () => void
  onSuccess?: () => void  // 등록 성공 시 콜백 (목록 갱신용)
  workspaces?: WorkspaceOption[]
  initialName?: string
  initialBlocks?: WorkspaceBlock[]
}

const CATEGORIES: Exclude<MarketCategory, "전체">[] = [
  "웹 자동화", "데이터 수집", "SNS 자동화", "업무 자동화", "쇼핑몰",
]

type Step = "select" | "info" | "pricing" | "preview" | "done"

export function SellModal({ onClose, onSuccess, workspaces = [], initialName = "", initialBlocks }: SellModalProps) {
  // If initialBlocks are passed directly (from a specific workspace), skip select step
  const hasDirectBlocks = Boolean(initialBlocks && initialBlocks.length > 0)
  const [step, setStep] = useState<Step>(hasDirectBlocks || workspaces.length === 0 ? "info" : "select")
  const [selectedWsId, setSelectedWsId] = useState<string | null>(
    hasDirectBlocks ? "__direct__" : workspaces[0]?.id ?? null
  )
  const [title, setTitle] = useState(initialName)
  const [description, setDescription] = useState("")
  const [features, setFeatures] = useState<string[]>([])
  const [usageSteps, setUsageSteps] = useState<string[]>([])
  const [category, setCategory] = useState<Exclude<MarketCategory, "전체">>("웹 자동화")
  const [price, setPrice] = useState<"free" | "paid">("free")
  const [priceValue, setPriceValue] = useState("9900")
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isGeneratingDesc, setIsGeneratingDesc] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectedWs = workspaces.find((w) => w.id === selectedWsId)
  const activeBlocks = hasDirectBlocks ? (initialBlocks ?? []) : (selectedWs?.blocks ?? [])

  const ALL_STEPS: Step[] = hasDirectBlocks || workspaces.length === 0
    ? ["info", "pricing", "preview", "done"]
    : ["select", "info", "pricing", "preview", "done"]

  const DISPLAY_STEPS: Step[] = ALL_STEPS.filter((s) => s !== "done")

  const stepIdx = ALL_STEPS.indexOf(step)

  const stepLabel: Record<Step, string> = {
    select:  "작업 선택",
    info:    "기본 정보",
    pricing: "가격 설정",
    preview: "미리보기",
    done:    "등록 완료",
  }

  const addTag = () => {
    const t = tagInput.trim()
    if (t && !tags.includes(t) && tags.length < 6) { setTags((p) => [...p, t]); setTagInput("") }
  }

  const canNext =
    step === "select"  ? Boolean(selectedWsId) && activeBlocks.length > 0
    : step === "info"    ? title.trim().length >= 5 && description.trim().length >= 10
    : step === "pricing" ? price === "free" || Number(priceValue) >= 1000
    : step === "preview" ? true
    : false

  const goNext = async () => {
    if (step === "preview") {
      // 실제 마켓플레이스에 등록
      setIsSubmitting(true)
      setError(null)
      try {
        await api.createMarketplaceItem({
          title,
          description,
          category,
          price: price === "free" ? 0 : Number(priceValue),
          tags,
          blocks_data: activeBlocks,
          block_colors: activeBlocks.map((b) => b.color),
          features,
          usage_steps: usageSteps,
        })
        setStep("done")
        // 등록 성공 시 목록 갱신
        onSuccess?.()
      } catch (err: any) {
        setError(err.message || "등록 중 오류가 발생했습니다.")
      } finally {
        setIsSubmitting(false)
      }
      return
    }

    // select → info 단계에서 AI로 개요, 주요 기능, 사용 방법 자동 생성
    if (step === "select" && activeBlocks.length > 0) {
      setIsGeneratingDesc(true)
      const wsName = selectedWs?.name || initialName || ""
      setTitle(wsName)

      try {
        const result = await api.analyzeBlocksForDescription(activeBlocks, wsName)
        setDescription(result.description)
        setFeatures(result.features || [])
        setUsageSteps(result.usage_steps || [])
      } catch (err) {
        console.error("개요 생성 오류:", err)
        // 실패 시 기본 설명
        const labels = activeBlocks.slice(0, 3).map(b => b.label).join(", ")
        setDescription(`${wsName || "자동화"} 워크플로우입니다. ${labels} 등 ${activeBlocks.length}개 블록으로 구성되어 있습니다.`)
        setFeatures(["자동으로 데이터를 수집하고 저장", "설정에 따라 반복 실행 지원", "간편한 설정으로 빠른 시작"])
        setUsageSteps(["워크스페이스에 템플릿을 가져옵니다", "각 블록의 설정값을 입력합니다", "실행 버튼을 눌러 자동화를 시작합니다"])
      } finally {
        setIsGeneratingDesc(false)
      }
    }

    const next = ALL_STEPS[stepIdx + 1]
    if (next) setStep(next)
  }

  const goPrev = () => {
    if (stepIdx === 0) { onClose(); return }
    const prev = ALL_STEPS[stepIdx - 1]
    if (prev) setStep(prev)
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-50 backdrop-blur-sm" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={(e) => e.stopPropagation()}>
        <div className="bg-background rounded-3xl shadow-2xl w-full max-w-lg flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200" onClick={(e) => e.stopPropagation()}>

          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b">
            <div>
              <h2 className="font-bold">내 자동화 판매하기</h2>
              <p className="text-xs text-muted-foreground mt-0.5">워크스페이스의 자동화를 마켓에 등록하세요</p>
            </div>
            <button onClick={onClose} className="w-8 h-8 rounded-xl hover:bg-secondary flex items-center justify-center">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Progress */}
          <div className="flex items-center gap-0 px-6 pt-4">
            {DISPLAY_STEPS.map((s, i) => (
              <div key={s} className="flex items-center flex-1 last:flex-none">
                <div className={`w-7 h-7 rounded-xl flex items-center justify-center text-xs font-bold flex-shrink-0 transition-colors ${
                  ALL_STEPS.indexOf(step) >= ALL_STEPS.indexOf(s) ? "bg-foreground text-background" : "bg-secondary text-muted-foreground"
                }`}>{i + 1}</div>
                <span className={`text-xs ml-1.5 font-medium transition-colors ${
                  ALL_STEPS.indexOf(step) >= ALL_STEPS.indexOf(s) ? "text-foreground" : "text-muted-foreground"
                }`}>{stepLabel[s]}</span>
                {i < DISPLAY_STEPS.length - 1 && (
                  <div className={`flex-1 h-px mx-2 ${ALL_STEPS.indexOf(step) > ALL_STEPS.indexOf(s) ? "bg-foreground" : "bg-border"}`} />
                )}
              </div>
            ))}
          </div>

          {/* Body */}
          <div className="p-6 space-y-4 flex-1 overflow-y-auto max-h-[60vh]">

            {/* Step: select workspace */}
            {step === "select" && (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">판매할 자동화가 담긴 워크스페이스를 선택하세요.</p>
                {workspaces.map((ws) => (
                  <button
                    key={ws.id}
                    onClick={() => setSelectedWsId(ws.id)}
                    className={`w-full text-left p-4 rounded-2xl border-2 transition-all ${
                      selectedWsId === ws.id ? "border-foreground bg-secondary/50" : "border-border hover:border-muted-foreground"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-muted flex items-center justify-center flex-shrink-0">
                        <Layers className="w-4 h-4 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-sm">{ws.name}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{ws.blocks.length}개 블록</p>
                      </div>
                      {ws.blocks.length === 0 && (
                        <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-xl">블록 없음</span>
                      )}
                    </div>
                    {ws.blocks.length > 0 && (
                      <div className="flex gap-1.5 mt-3 flex-wrap">
                        {ws.blocks.slice(0, 5).map((b) => (
                          <span key={b.instanceId} className="text-[11px] px-2 py-0.5 rounded-xl font-medium text-white" style={{ backgroundColor: b.color }}>
                            {b.label}
                          </span>
                        ))}
                        {ws.blocks.length > 5 && (
                          <span className="text-[11px] px-2 py-0.5 rounded-xl bg-secondary text-muted-foreground">+{ws.blocks.length - 5}</span>
                        )}
                      </div>
                    )}
                  </button>
                ))}
                {workspaces.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <Layers className="w-8 h-8 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">빌더에 워크스페이스가 없습니다.</p>
                  </div>
                )}
              </div>
            )}

            {/* Step: info */}
            {step === "info" && (
              <>
                <div>
                  <label className="text-xs font-semibold mb-1.5 block">자동화 이름 <span className="text-red-500">*</span></label>
                  <Input placeholder="예: 네이버 쇼핑 최저가 수집기" value={title} onChange={(e) => setTitle(e.target.value)} className="rounded-xl h-10" maxLength={40} />
                  <p className="text-[11px] text-muted-foreground mt-1 text-right">{title.length}/40</p>
                </div>
                <div>
                  <label className="text-xs font-semibold mb-1.5 block">설명 <span className="text-red-500">*</span></label>
                  <textarea
                    placeholder="어떤 작업을 자동화하는지 구체적으로 설명해주세요. (최소 10자)"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full h-24 px-3 py-2.5 rounded-xl border bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                    maxLength={200}
                  />
                  <p className="text-[11px] text-muted-foreground text-right">{description.length}/200</p>
                </div>
                <div>
                  <label className="text-xs font-semibold mb-1.5 block">카테고리</label>
                  <div className="flex flex-wrap gap-2">
                    {CATEGORIES.map((cat) => (
                      <button key={cat} onClick={() => setCategory(cat)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${category === cat ? "bg-foreground text-background" : "bg-secondary text-secondary-foreground hover:bg-secondary/70"}`}
                      >{cat}</button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs font-semibold mb-1.5 block">태그 (최대 6개)</label>
                  <div className="flex gap-2">
                    <Input placeholder="태그 입력 후 Enter" value={tagInput} onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addTag())}
                      className="rounded-xl h-9 text-sm flex-1" />
                    <Button size="sm" variant="outline" className="rounded-xl h-9 px-3" onClick={addTag}><Plus className="w-3.5 h-3.5" /></Button>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {tags.map((tag) => (
                      <span key={tag} className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-xl bg-secondary">
                        {tag}
                        <button onClick={() => setTags((p) => p.filter((t) => t !== tag))}><Minus className="w-3 h-3 text-muted-foreground hover:text-foreground" /></button>
                      </span>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* Step: pricing */}
            {step === "pricing" && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  {(["free", "paid"] as const).map((p) => (
                    <button key={p} onClick={() => setPrice(p)}
                      className={`p-4 rounded-2xl border-2 text-left transition-all ${price === p ? "border-foreground bg-secondary/50" : "border-border hover:border-muted-foreground"}`}
                    >
                      <div className="font-bold text-base mb-1">{p === "free" ? "무료" : "유료"}</div>
                      <p className="text-xs text-muted-foreground">{p === "free" ? "누구나 무료로 사용할 수 있게 공개합니다" : "가격을 설정하고 수익을 창출합니다 (수수료 20%)"}</p>
                    </button>
                  ))}
                </div>
                {price === "paid" && (
                  <div>
                    <label className="text-xs font-semibold mb-1.5 block">판매 가격 (원)</label>
                    <div className="flex items-center gap-2">
                      <Input type="number" value={priceValue} onChange={(e) => setPriceValue(e.target.value)} className="rounded-xl h-10" min={1000} step={100} />
                      <span className="text-sm text-muted-foreground flex-shrink-0">원</span>
                    </div>
                    <div className="mt-3 p-3 bg-secondary/50 rounded-xl flex items-start gap-2">
                      <Info className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                      <div className="text-xs text-muted-foreground space-y-0.5">
                        <p>판매가: <span className="text-foreground font-semibold">{Number(priceValue||0).toLocaleString()}원</span></p>
                        <p>플랫폼 수수료 (20%): {Math.round(Number(priceValue||0)*0.2).toLocaleString()}원</p>
                        <p>예상 수익: <span className="text-green-600 font-semibold">{Math.round(Number(priceValue||0)*0.8).toLocaleString()}원</span></p>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Step: preview */}
            {step === "preview" && (
              <div>
                <p className="text-xs text-muted-foreground mb-4">마켓에 노출될 모습을 확인하세요.</p>
                <div className="border rounded-2xl overflow-hidden">
                  <div className="bg-muted/50 h-24 flex items-center justify-center px-4">
                    <div className="flex flex-col gap-1.5 w-full">
                      {["#22c55e","#3b82f6","#a855f7","#f97316"].map((c, i) => (
                        <div key={i} className="h-4 rounded-lg opacity-80" style={{ backgroundColor: c, width: `${85-i*8}%` }} />
                      ))}
                    </div>
                  </div>
                  <div className="p-4">
                    <h3 className="font-semibold text-sm mb-1">{title || "자동화 제목"}</h3>
                    <p className="text-xs text-muted-foreground line-clamp-2">{description || "설명이 여기에 표시됩니다."}</p>
                    <div className="flex flex-wrap gap-1 mt-2">{tags.map((t) => <span key={t} className="text-[10px] px-2 py-0.5 rounded-full bg-secondary">{t}</span>)}</div>
                    <div className="flex items-center justify-between mt-3 pt-3 border-t">
                      <span className="text-xs text-muted-foreground flex items-center gap-1"><BadgeCheck className="w-3.5 h-3.5 text-blue-500" /> 내 계정</span>
                      <span className="text-sm font-bold">{price === "free" ? "무료" : `${Number(priceValue||0).toLocaleString()}원`}</span>
                    </div>
                  </div>
                </div>
                <div className="mt-3 p-3 bg-secondary/50 rounded-xl">
                  <p className="text-xs text-muted-foreground">포함된 블록: <span className="text-foreground font-medium">{activeBlocks.length}개</span></p>
                </div>
                {error && (
                  <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl">
                    <p className="text-xs text-red-600">{error}</p>
                  </div>
                )}
              </div>
            )}

            {/* Step: done */}
            {step === "done" && (
              <div className="py-6 text-center">
                <div className="w-16 h-16 rounded-3xl bg-green-100 flex items-center justify-center mx-auto mb-4">
                  <BadgeCheck className="w-8 h-8 text-green-600" />
                </div>
                <h3 className="text-lg font-bold mb-2">등록 완료!</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">마켓플레이스에 자동화가 등록되었습니다.<br />지금 바로 확인할 수 있습니다.</p>
              </div>
            )}
          </div>

          {/* Footer */}
          {step !== "done" ? (
            <div className="flex items-center justify-between px-6 py-4 border-t flex-shrink-0">
              <Button variant="ghost" className="rounded-xl" onClick={goPrev} disabled={isSubmitting || isGeneratingDesc}>{stepIdx === 0 ? "취소" : "이전"}</Button>
              <Button className="rounded-xl px-6" disabled={!canNext || isSubmitting || isGeneratingDesc} onClick={goNext}>
                {isSubmitting ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" />등록 중...</>
                ) : isGeneratingDesc ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" />AI 분석 중...</>
                ) : step === "preview" ? "마켓에 등록하기" : "다음"}
              </Button>
            </div>
          ) : (
            <div className="px-6 py-4 border-t">
              <Button className="w-full rounded-xl" onClick={onClose}>닫기</Button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
