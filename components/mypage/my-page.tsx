"use client"

import { useState, useEffect, useCallback } from "react"
import { api } from "@/lib/api"
import { useAuth } from "@/contexts/auth-context"
import {
  User, Package, ShoppingBag, BarChart3, Settings, Bell,
  Star, Download, TrendingUp, Edit3, Trash2, Eye, EyeOff,
  ToggleLeft, ToggleRight, ChevronRight, Shield, CreditCard,
  CheckCircle, Clock, AlertCircle, X, AlertTriangle, MessageSquare,
  RefreshCw, RotateCcw, PanelTop, Plus, Minus, BadgeCheck, Info, Layers, Monitor,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { WorkspaceBlock } from "@/types/blocks"
import { AgentSetupGuide } from "@/components/blocks/agent-setup-guide"

// ─── Add to workspace modal ──────────────────────────────────────────────────
function AddToWorkspaceModal({
  purchase,
  onClose,
  onConfirm,
}: {
  purchase: Purchase
  onClose: () => void
  onConfirm: (sheetName: string) => void
}) {
  const [name, setName] = useState(purchase.name)
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-background rounded-3xl shadow-2xl p-6 w-full max-w-sm mx-4 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <PanelTop className="w-4 h-4 text-primary" />
            </div>
            <h3 className="font-bold text-sm">워크스페이스에 추가</h3>
          </div>
          <button onClick={onClose} className="w-7 h-7 rounded-xl hover:bg-secondary flex items-center justify-center">
            <X className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          새 작업 탭의 이름을 입력하세요. 빌더에 새 시트로 추가됩니다.
        </p>
        <div>
          <label className="text-xs text-muted-foreground mb-1.5 block">탭 이름</label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded-xl h-9 text-sm"
            placeholder="작업 이름 입력"
            autoFocus
            onKeyDown={(e) => e.key === "Enter" && !e.nativeEvent.isComposing && name.trim() && onConfirm(name.trim())}
          />
        </div>
        <div className="flex gap-2 pt-1">
          <Button variant="outline" className="flex-1 rounded-xl" onClick={onClose}>취소</Button>
          <Button
            className="flex-1 rounded-xl gap-1.5"
            disabled={!name.trim()}
            onClick={() => onConfirm(name.trim())}
          >
            <PanelTop className="w-3.5 h-3.5" />
            추가하기
          </Button>
        </div>
      </div>
    </div>
  )
}

type MyPageTab = "dashboard" | "templates" | "purchases" | "settings"
type PurchaseTab = "active" | "pending" | "cancelled"

interface SoldTemplate {
  id: string
  name: string
  price: number
  downloads: number
  revenue: number
  rating: number
  reviews: number
  status: "active" | "draft" | "suspended"
  createdAt: string
  blocks: WorkspaceBlock[]
}

interface Purchase {
  id: string
  itemId: string  // marketplace item id for reviews
  name: string
  price: number
  purchasedAt: string
  creator: string
  status: "active" | "pending" | "cancelled"
  /** ISO string — 3 days after purchase */
  deadline?: string
  myReview?: { rating: number; text: string }
}

interface MyPageProps {
  soldTemplates?: SoldTemplate[]
  onEditTemplate?: (t: SoldTemplate) => void
  onAddToWorkspace?: (purchase: Purchase, sheetName: string) => void
}

function daysFromNow(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString()
}

const TEMPLATE_STATUS_LABEL: Record<string, { label: string; color: string; icon: typeof CheckCircle }> = {
  active:    { label: "판매중",   color: "text-green-600 bg-green-50",  icon: CheckCircle },
  draft:     { label: "임시저장", color: "text-amber-600 bg-amber-50",  icon: Clock },
  suspended: { label: "판매중단", color: "text-red-600 bg-red-50",      icon: AlertCircle },
}

// ─── Edit template modal (판매등록과 동일한 2단계: 기본정보 → 가격설정) ──────
const EDIT_CATEGORIES = ["웹 자동화", "데이터 수집", "SNS 자동화", "업무 자동화", "쇼핑몰"] as const

function EditTemplateModal({
  template,
  onClose,
  onSave,
}: {
  template: SoldTemplate
  onClose: () => void
  onSave: (updated: SoldTemplate) => void
}) {
  type EditStep = "info" | "pricing"
  const STEPS: EditStep[] = ["info", "pricing"]
  const stepLabel: Record<EditStep, string> = { info: "기본 정보", pricing: "가격 설정" }

  const [step, setStep] = useState<EditStep>("info")
  const [name, setName] = useState(template.name)
  const [description, setDescription] = useState("")
  const [category, setCategory] = useState(EDIT_CATEGORIES[0])
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState("")
  const [priceType, setPriceType] = useState<"free" | "paid">(template.price === 0 ? "free" : "paid")
  const [priceValue, setPriceValue] = useState(String(template.price || 9900))
  const [status, setStatus] = useState(template.status)

  const addTag = () => {
    const t = tagInput.trim()
    if (t && !tags.includes(t) && tags.length < 6) { setTags((p) => [...p, t]); setTagInput("") }
  }

  const canNext =
    step === "info" ? name.trim().length >= 2 && description.trim().length >= 5
    : priceType === "free" || Number(priceValue) >= 1000

  const handleSave = () => {
    const finalPrice = priceType === "free" ? 0 : Number(priceValue)
    onSave({ ...template, name: name.trim(), price: finalPrice, status })
  }

  const stepIdx = STEPS.indexOf(step)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-background rounded-3xl shadow-2xl w-full max-w-lg mx-4 flex flex-col overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div>
            <h2 className="font-bold">템플릿 수정</h2>
            <p className="text-xs text-muted-foreground mt-0.5">{template.name}</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-xl hover:bg-secondary flex items-center justify-center">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Progress */}
        <div className="flex items-center gap-0 px-6 pt-4">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center flex-1 last:flex-none">
              <div className={`w-7 h-7 rounded-xl flex items-center justify-center text-xs font-bold flex-shrink-0 transition-colors ${
                stepIdx >= i ? "bg-foreground text-background" : "bg-secondary text-muted-foreground"
              }`}>{i + 1}</div>
              <span className={`text-xs ml-1.5 font-medium ${stepIdx >= i ? "text-foreground" : "text-muted-foreground"}`}>{stepLabel[s]}</span>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-px mx-2 ${stepIdx > i ? "bg-foreground" : "bg-border"}`} />
              )}
            </div>
          ))}
        </div>

        {/* Body */}
        <div className="p-6 space-y-4 overflow-y-auto max-h-[55vh]">
          {step === "info" && (
            <>
              <div>
                <label className="text-xs font-semibold mb-1.5 block">자동화 이름 <span className="text-red-500">*</span></label>
                <Input value={name} onChange={(e) => setName(e.target.value)} className="rounded-xl h-10" maxLength={40} autoFocus />
                <p className="text-[11px] text-muted-foreground mt-1 text-right">{name.length}/40</p>
              </div>
              <div>
                <label className="text-xs font-semibold mb-1.5 block">설명 <span className="text-red-500">*</span></label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="어떤 작업을 자동화하는지 구체적으로 설명해주세요. (최소 5자)"
                  className="w-full h-24 px-3 py-2.5 rounded-xl border bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                  maxLength={200}
                />
                <p className="text-[11px] text-muted-foreground text-right">{description.length}/200</p>
              </div>
              <div>
                <label className="text-xs font-semibold mb-1.5 block">카테고리</label>
                <div className="flex flex-wrap gap-2">
                  {EDIT_CATEGORIES.map((cat) => (
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
                    onKeyDown={(e) => e.key === "Enter" && !e.nativeEvent.isComposing && (e.preventDefault(), addTag())}
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
              <div>
                <label className="text-xs font-semibold mb-1.5 block">상태</label>
                <div className="flex gap-2">
                  {(["active", "draft", "suspended"] as const).map((s) => {
                    const labels = { active: "판매중", draft: "임시저장", suspended: "판매중단" }
                    return (
                      <button key={s} onClick={() => setStatus(s)}
                        className={`flex-1 py-2 rounded-xl text-xs font-medium border transition-colors ${
                          status === s ? "bg-foreground text-background border-foreground" : "border-border text-muted-foreground hover:border-foreground/30"
                        }`}
                      >{labels[s]}</button>
                    )
                  })}
                </div>
              </div>
            </>
          )}

          {step === "pricing" && (
            <>
              <div className="grid grid-cols-2 gap-3">
                {(["free", "paid"] as const).map((p) => (
                  <button key={p} onClick={() => setPriceType(p)}
                    className={`p-4 rounded-2xl border-2 text-left transition-all ${priceType === p ? "border-foreground bg-secondary/50" : "border-border hover:border-muted-foreground"}`}
                  >
                    <div className="font-bold text-base mb-1">{p === "free" ? "무료" : "유료"}</div>
                    <p className="text-xs text-muted-foreground">{p === "free" ? "누구나 무료로 사용할 수 있게 공개합니다" : "가격을 설정하고 수익을 창출합니다 (수수료 20%)"}</p>
                  </button>
                ))}
              </div>
              {priceType === "paid" && (
                <div>
                  <label className="text-xs font-semibold mb-1.5 block">판매 가격 (원)</label>
                  <div className="flex items-center gap-2">
                    <Input type="number" value={priceValue} onChange={(e) => setPriceValue(e.target.value)} className="rounded-xl h-10" min={1000} step={100} />
                    <span className="text-sm text-muted-foreground flex-shrink-0">원</span>
                  </div>
                  <div className="mt-3 p-3 bg-secondary/50 rounded-xl flex items-start gap-2">
                    <Info className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-muted-foreground space-y-0.5">
                      <p>판매가: <span className="text-foreground font-semibold">{Number(priceValue || 0).toLocaleString()}원</span></p>
                      <p>플랫폼 수수료 (20%): {Math.round(Number(priceValue || 0) * 0.2).toLocaleString()}원</p>
                      <p>예상 수익: <span className="text-green-600 font-semibold">{Math.round(Number(priceValue || 0) * 0.8).toLocaleString()}원</span></p>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t flex-shrink-0">
          <Button variant="ghost" className="rounded-xl" onClick={() => stepIdx === 0 ? onClose() : setStep("info")}>
            {stepIdx === 0 ? "취소" : "이전"}
          </Button>
          {step === "info" ? (
            <Button className="rounded-xl px-6" disabled={!canNext} onClick={() => setStep("pricing")}>다음</Button>
          ) : (
            <Button className="rounded-xl px-6" disabled={!canNext} onClick={handleSave}>저장</Button>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Delete confirm dialog ───────────────────────────────────────────────────
function DeleteConfirmDialog({
  name,
  step,
  onStep,
  onCancel,
  onConfirm,
}: {
  name: string
  step: 1 | 2
  onStep: () => void
  onCancel: () => void
  onConfirm: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative bg-background rounded-3xl shadow-2xl p-6 w-full max-w-sm mx-4 space-y-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 ${step === 1 ? "bg-amber-100" : "bg-red-100"}`}>
            <AlertTriangle className={`w-5 h-5 ${step === 1 ? "text-amber-600" : "text-red-600"}`} />
          </div>
          <div>
            <h3 className="font-bold text-sm">{step === 1 ? "정말 삭제하시겠어요?" : "최종 확인 — 복구 불가"}</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              {step === 1
                ? `"${name}" 템플릿을 삭제합니다.`
                : "삭제하면 데이터를 복구할 수 없습니다."}
            </p>
          </div>
        </div>
        {step === 2 && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3">
            <p className="text-xs text-red-700 font-medium">이 작업은 되돌릴 수 없습니다. 모든 판매 데이터가 함께 삭제됩니다.</p>
          </div>
        )}
        <div className="flex gap-2 pt-1">
          <Button variant="outline" className="flex-1 rounded-xl" onClick={onCancel}>취소</Button>
          <Button
            className={`flex-1 rounded-xl ${step === 2 ? "bg-red-600 hover:bg-red-700 text-white" : ""}`}
            variant={step === 1 ? "default" : "default"}
            onClick={step === 1 ? onStep : onConfirm}
          >
            {step === 1 ? "계속 진행" : "완전히 삭제"}
          </Button>
        </div>
      </div>
    </div>
  )
}

// ─── Review modal ────────────────────────────────────────────────────────────
function ReviewModal({
  purchase,
  onClose,
  onSubmit,
}: {
  purchase: Purchase
  onClose: () => void
  onSubmit: (rating: number, text: string) => void
}) {
  const [rating, setRating] = useState(purchase.myReview?.rating ?? 0)
  const [text, setText] = useState(purchase.myReview?.text ?? "")
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-background rounded-3xl shadow-2xl p-6 w-full max-w-sm mx-4 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-bold">리뷰 작성</h3>
          <button onClick={onClose} className="w-7 h-7 rounded-xl hover:bg-secondary flex items-center justify-center"><X className="w-4 h-4" /></button>
        </div>
        <p className="text-sm text-muted-foreground">{purchase.name}</p>
        {/* Star rating */}
        <div className="flex gap-1.5">
          {[1,2,3,4,5].map((s) => (
            <button key={s} onClick={() => setRating(s)}>
              <Star className={`w-7 h-7 transition-colors ${s <= rating ? "text-amber-400 fill-amber-400" : "text-muted stroke-muted-foreground"}`} />
            </button>
          ))}
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="사용 후기를 자세히 남겨주세요. (최소 10자)"
          className="w-full h-24 px-3 py-2.5 rounded-xl border bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
          maxLength={300}
        />
        <p className="text-right text-[11px] text-muted-foreground">{text.length}/300</p>
        <Button
          className="w-full rounded-xl"
          disabled={rating === 0 || text.length < 10}
          onClick={() => onSubmit(rating, text)}
        >
          리뷰 등록
        </Button>
      </div>
    </div>
  )
}

// ─── Cancel confirm dialog ───────────────────────────────────────────────────
function CancelConfirmDialog({
  purchase,
  onClose,
  onConfirm,
}: {
  purchase: Purchase
  onClose: () => void
  onConfirm: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-background rounded-3xl shadow-2xl p-6 w-full max-w-sm mx-4 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-amber-100 flex items-center justify-center flex-shrink-0">
            <RotateCcw className="w-5 h-5 text-amber-600" />
          </div>
          <div>
            <h3 className="font-bold text-sm">구매 취소 및 환불</h3>
            <p className="text-xs text-muted-foreground mt-0.5">"{purchase.name}"</p>
          </div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 space-y-1">
          <p className="text-xs text-amber-800 font-medium">취소 시 주의사항</p>
          <p className="text-xs text-amber-700">• 취소 후 워크스페이스에서 이 자동화를 사용할 수 없습니다.</p>
          <p className="text-xs text-amber-700">• 환불은 1~3 영업일 내 처리됩니다.</p>
          <p className="text-xs text-amber-700 font-semibold">• 환불 금액: {purchase.price.toLocaleString()}원</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="flex-1 rounded-xl" onClick={onClose}>유지하기</Button>
          <Button className="flex-1 rounded-xl bg-amber-600 hover:bg-amber-700 text-white" onClick={onConfirm}>
            취소 및 환불
          </Button>
        </div>
      </div>
    </div>
  )
}

// ─── Main component ──────────────────────────────────��───────────────────────
export function MyPage({ soldTemplates: initialTemplates = [], onEditTemplate, onAddToWorkspace }: MyPageProps) {
  const { user } = useAuth()
  const [tab, setTab] = useState<MyPageTab>("dashboard")
  const [purchaseTab, setPurchaseTab] = useState<PurchaseTab>("active")
  const [templates, setTemplates] = useState<SoldTemplate[]>(initialTemplates)
  const [purchases, setPurchases] = useState<Purchase[]>([])
  const [profileName, setProfileName] = useState(user?.name || "")
  const [profileEmail, setProfileEmail] = useState(user?.email || "")
  const [editingProfile, setEditingProfile] = useState(false)
  const [notifEmail, setNotifEmail] = useState(true)
  const [notifSale, setNotifSale] = useState(true)
  const [notifReview, setNotifReview] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [stats, setStats] = useState({ avgRating: 0, revenueHistory: [0, 0, 0, 0, 0, 0] as number[], monthlyRevenue: 0 })
  const [showDeleteAccount, setShowDeleteAccount] = useState(false)
  const [deleteAccountStep, setDeleteAccountStep] = useState<1 | 2>(1)
  const { logout } = useAuth()

  // Load data from API
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      try {
        const [templatesRes, purchasesRes, statsRes] = await Promise.all([
          api.getMyTemplates().catch(() => ({ templates: [], total: 0 })),
          api.getPurchases().catch(() => ({ active: [], pending: [], cancelled: [] })),
          api.getMyStats().catch(() => ({ templates_count: 0, total_downloads: 0, total_revenue: 0, avg_rating: 0, active_purchases: 0 })),
        ])

        setTemplates(templatesRes.templates.map((t: any) => ({
          id: t.id,
          name: t.name,
          price: t.price,
          downloads: t.downloads,
          revenue: t.revenue,
          rating: t.rating,
          reviews: t.reviews,
          status: t.status,
          createdAt: new Date(t.created_at).toLocaleDateString(),
          blocks: t.blocks_data || [],
        })))

        const allPurchases: Purchase[] = [
          ...(purchasesRes.active || []).map((p: any) => ({ id: p.id, itemId: p.item_id, name: p.name, price: p.price, purchasedAt: new Date(p.purchased_at).toLocaleDateString(), creator: p.creator, status: "active" as const, deadline: p.deadline, myReview: p.my_review })),
          ...(purchasesRes.pending || []).map((p: any) => ({ id: p.id, itemId: p.item_id, name: p.name, price: p.price, purchasedAt: new Date(p.purchased_at).toLocaleDateString(), creator: p.creator, status: "pending" as const, deadline: p.deadline, myReview: p.my_review })),
          ...(purchasesRes.cancelled || []).map((p: any) => ({ id: p.id, itemId: p.item_id, name: p.name, price: p.price, purchasedAt: new Date(p.purchased_at).toLocaleDateString(), creator: p.creator, status: "cancelled" as const, deadline: p.deadline, myReview: p.my_review })),
        ]
        setPurchases(allPurchases)

        setStats({
          avgRating: statsRes.avg_rating || 0,
          revenueHistory: [0, 0, 0, 0, 0, statsRes.total_revenue || 0],
          monthlyRevenue: statsRes.total_revenue || 0,
        })
      } catch {
        // Use empty data on error
      } finally {
        setIsLoading(false)
      }
    }
    loadData()
  }, [])

  // Delete flow
  const [editTarget, setEditTarget] = useState<SoldTemplate | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<SoldTemplate | null>(null)
  const [deleteStep, setDeleteStep] = useState<1 | 2>(1)

  // Review flow
  const [reviewTarget, setReviewTarget] = useState<Purchase | null>(null)

  // Cancel flow
  const [cancelTarget, setCancelTarget] = useState<Purchase | null>(null)

  // Add to workspace flow
  const [addTarget, setAddTarget] = useState<Purchase | null>(null)

  const totalRevenue = templates.reduce((s, t) => s + t.revenue, 0)
  const totalDownloads = templates.reduce((s, t) => s + t.downloads, 0)

  const TABS: { id: MyPageTab; label: string; icon: typeof User }[] = [
    { id: "dashboard", label: "대시보드", icon: BarChart3 },
    { id: "templates", label: "내 템플릿", icon: Package },
    { id: "purchases", label: "구매 목록", icon: ShoppingBag },
    { id: "settings",  label: "설정",     icon: Settings },
  ]

  const activePurchases   = purchases.filter((p) => p.status === "active")
  const pendingPurchases  = purchases.filter((p) => p.status === "pending")
  const cancelledPurchases = purchases.filter((p) => p.status === "cancelled")

  function getRemainingDays(deadline: string) {
    const ms = new Date(deadline).getTime() - Date.now()
    return Math.max(0, Math.ceil(ms / 86400000))
  }

  async function handleSaveTemplate(updated: SoldTemplate) {
    try {
      await api.updateTemplate(updated.id, {
        name: updated.name,
        price: updated.price,
        status: updated.status,
      })
      setTemplates((prev) => prev.map((t) => t.id === updated.id ? updated : t))
      setEditTarget(null)
    } catch (error) {
      console.error("템플릿 수정 실패:", error)
    }
  }

  async function handleDeleteTemplate() {
    if (!deleteTarget) return
    try {
      await api.deleteTemplate(deleteTarget.id)
      setTemplates((prev) => prev.filter((t) => t.id !== deleteTarget.id))
      setDeleteTarget(null)
      setDeleteStep(1)
    } catch (error) {
      console.error("템플릿 삭제 실패:", error)
    }
  }

  async function handleConfirmPurchase(id: string) {
    try {
      await api.confirmPurchase(id)
      setPurchases((prev) => prev.map((p) => p.id === id ? { ...p, status: "active" } : p))
    } catch (error) {
      console.error("구매 확정 실패:", error)
    }
  }

  async function handleCancelPurchase() {
    if (!cancelTarget) return
    try {
      await api.cancelPurchase(cancelTarget.id)
      setPurchases((prev) => prev.map((p) => p.id === cancelTarget.id ? { ...p, status: "cancelled", deadline: undefined } : p))
      setCancelTarget(null)
    } catch (error) {
      console.error("구매 취소 실패:", error)
    }
  }

  async function handleSubmitReview(rating: number, text: string) {
    if (!reviewTarget) return
    try {
      await api.createReview(reviewTarget.itemId, { rating, text })
      setPurchases((prev) => prev.map((p) => p.id === reviewTarget.id ? { ...p, myReview: { rating, text } } : p))
      setReviewTarget(null)
    } catch (error) {
      console.error("리뷰 작성 실패:", error)
    }
  }

  async function toggleTemplateStatus(id: string) {
    const template = templates.find((t) => t.id === id)
    if (!template) return
    const newStatus = template.status === "active" ? "suspended" : "active"
    try {
      await api.updateTemplate(id, { status: newStatus })
      setTemplates((prev) => prev.map((t) =>
        t.id === id ? { ...t, status: newStatus } : t
      ))
    } catch (error) {
      console.error("상태 변경 실패:", error)
    }
  }

  async function handleSaveProfile() {
    try {
      await api.updateProfile({ name: profileName })
      setEditingProfile(false)
    } catch (error) {
      console.error("프로필 저장 실패:", error)
    }
  }

  return (
    <div className="h-full flex overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className="w-56 border-r flex-shrink-0 flex flex-col">
        <div className="p-5 border-b">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-foreground flex items-center justify-center text-background font-bold text-lg flex-shrink-0">
              {profileName[0]}
            </div>
            <div className="min-w-0">
              <p className="font-semibold text-sm truncate">{profileName}</p>
              <p className="text-xs text-muted-foreground truncate">{profileEmail}</p>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-1 text-xs">
            <Shield className="w-3 h-3 text-blue-500" />
            <span className="text-blue-600 font-medium">인증된 제작자</span>
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-0.5">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                tab === id ? "bg-foreground text-background" : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
              {id === "purchases" && pendingPurchases.length > 0 && (
                <span className="ml-auto text-xs bg-amber-500 text-white rounded-full w-4 h-4 flex items-center justify-center font-bold">
                  {pendingPurchases.length}
                </span>
              )}
            </button>
          ))}
        </nav>
        <div className="p-3 border-t">
          <div className="text-xs text-muted-foreground text-center">AutoFlow v1.0</div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-8 max-w-3xl">

          {/* ── Dashboard ── */}
          {tab === "dashboard" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold mb-1">대시보드</h2>
                <p className="text-sm text-muted-foreground">내 자동화 템플릿 판매 현황을 확인하세요.</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: "총 수익",          value: `${totalRevenue.toLocaleString()}원`,   sub: stats.monthlyRevenue > 0 ? `이번 달 +${stats.monthlyRevenue.toLocaleString()}원` : "이번 달 수익 없음", icon: TrendingUp, color: "text-green-600" },
                  { label: "총 다운로드",       value: totalDownloads.toLocaleString(),        sub: `${templates.filter(t=>t.status==="active").length}개 템플릿`, icon: Download, color: "text-blue-600" },
                  { label: "평균 평점",         value: stats.avgRating.toFixed(1),        sub: `${templates.reduce((s,t)=>s+t.reviews,0)}개 리뷰`, icon: Star, color: "text-amber-500" },
                  { label: "판매 중인 템플릿",  value: templates.filter(t=>t.status==="active").length, sub: "활성 상태", icon: Package, color: "text-purple-600" },
                ].map(({ label, value, sub, icon: Icon, color }) => (
                  <div key={label} className="border rounded-2xl p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-muted-foreground">{label}</p>
                      <Icon className={`w-4 h-4 ${color}`} />
                    </div>
                    <p className="text-2xl font-bold">{value}</p>
                    <p className="text-xs text-muted-foreground">{sub}</p>
                  </div>
                ))}
              </div>
              <div className="border rounded-2xl p-5">
                <h3 className="text-sm font-semibold mb-4">월별 수익</h3>
                <div className="flex items-end gap-2 h-24">
                  {stats.revenueHistory.map((v, i) => {
                    const max = Math.max(...stats.revenueHistory)
                    const months = ["9월","10월","11월","12월","1월","2월"]
                    return (
                      <div key={i} className="flex-1 flex flex-col items-center gap-1">
                        <div
                          className={`w-full rounded-lg ${i === 5 ? "bg-foreground" : "bg-muted"}`}
                          style={{ height: `${(v/max)*100}%`, minHeight: 4 }}
                        />
                        <span className="text-xs text-muted-foreground">{months[i]}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
              <div className="border rounded-2xl overflow-hidden">
                <div className="px-5 py-3 border-b flex items-center justify-between">
                  <h3 className="text-sm font-semibold">최근 템플릿</h3>
                  <button onClick={() => setTab("templates")} className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1">
                    전체 보기 <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
                {templates.slice(0,3).map((t) => {
                  const s = TEMPLATE_STATUS_LABEL[t.status]
                  return (
                    <div key={t.id} className="px-5 py-3 border-b last:border-b-0 flex items-center gap-4">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{t.name}</p>
                        <p className="text-xs text-muted-foreground">{t.createdAt}</p>
                      </div>
                      <span className={`text-xs px-2.5 py-0.5 rounded-xl font-medium ${s.color}`}>{s.label}</span>
                      <p className="text-sm font-semibold w-24 text-right">{t.revenue.toLocaleString()}원</p>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* ── Templates ── */}
          {tab === "templates" && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-bold mb-1">판매 중인 템플릿</h2>
                <p className="text-sm text-muted-foreground">마켓플레이스에 등록한 자동화 템플릿을 관리하세요.</p>
              </div>
              <div className="space-y-3">
                {templates.map((t) => {
                  const s = TEMPLATE_STATUS_LABEL[t.status]
                  const Icon = s.icon
                  return (
                    <div key={t.id} className="border rounded-2xl p-5 space-y-4">
                      <div className="flex items-start gap-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold">{t.name}</h3>
                            <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-xl font-medium ${s.color}`}>
                              <Icon className="w-3 h-3" />{s.label}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground">{t.createdAt} 등록 · {t.price === 0 ? "무료" : `${t.price.toLocaleString()}원`}</p>
                        </div>
                        <div className="flex gap-1.5">
                          <button onClick={() => setEditTarget(t)} className="p-2 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
                            <Edit3 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => toggleTemplateStatus(t.id)}
                            className="p-2 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                            title={t.status === "active" ? "판매 중단" : "판매 재개"}
                          >
                            {t.status === "active" ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                          <button
                            onClick={() => { setDeleteTarget(t); setDeleteStep(1) }}
                            className="p-2 rounded-xl hover:bg-muted text-red-400 hover:text-red-600 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      <div className="grid grid-cols-4 gap-3">
                        {[
                          { label: "다운로드", value: t.downloads.toLocaleString() },
                          { label: "수익",     value: `${t.revenue.toLocaleString()}원` },
                          { label: "평점",     value: t.rating.toFixed(1) },
                          { label: "리뷰",     value: `${t.reviews}개` },
                        ].map(({ label, value }) => (
                          <div key={label} className="bg-muted/50 rounded-xl p-3 text-center">
                            <p className="text-xs text-muted-foreground mb-1">{label}</p>
                            <p className="text-sm font-semibold">{value}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })}
                {templates.length === 0 && (
                  <div className="text-center py-16 text-muted-foreground">
                    <Package className="w-10 h-10 mx-auto mb-3 opacity-30" />
                    <p className="text-sm">아직 등록된 템플릿이 없습니다.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Purchases ── */}
          {tab === "purchases" && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-bold mb-1">구매 목록</h2>
                <p className="text-sm text-muted-foreground">구매한 자동화 템플릿을 관리하세요.</p>
              </div>

              {/* Sub tabs */}
              <div className="flex gap-1 bg-secondary rounded-2xl p-1 w-fit">
                {([
                  { id: "active" as PurchaseTab,    label: "이용 중",      count: activePurchases.length },
                  { id: "pending" as PurchaseTab,   label: "구매 확정 대기", count: pendingPurchases.length },
                  { id: "cancelled" as PurchaseTab, label: "취소/환불",     count: cancelledPurchases.length },
                ] as const).map(({ id, label, count }) => (
                  <button
                    key={id}
                    onClick={() => setPurchaseTab(id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium transition-all ${
                      purchaseTab === id ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {label}
                    {count > 0 && (
                      <span className={`text-xs rounded-full px-1.5 font-bold ${
                        purchaseTab === id ? "bg-foreground text-background" : "bg-muted text-muted-foreground"
                      }`}>{count}</span>
                    )}
                  </button>
                ))}
              </div>

              {/* Active purchases */}
              {purchaseTab === "active" && (
                <div className="space-y-3">
                  {activePurchases.map((p) => (
                    <div key={p.id} className="border rounded-2xl p-5 flex items-center gap-4">
                      <div className="w-10 h-10 rounded-xl bg-muted flex items-center justify-center flex-shrink-0">
                        <Package className="w-5 h-5 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm">{p.name}</p>
                        <p className="text-xs text-muted-foreground">{p.creator} · {p.purchasedAt}</p>
                      </div>
                      <span className={`text-xs px-2.5 py-0.5 rounded-xl font-medium flex-shrink-0 ${p.price === 0 ? "bg-green-50 text-green-600" : "bg-blue-50 text-blue-600"}`}>
                        {p.price === 0 ? "무료" : `${p.price.toLocaleString()}원`}
                      </span>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {p.myReview ? (
                          <div className="flex items-center gap-1 text-xs text-amber-500">
                            <Star className="w-3.5 h-3.5 fill-amber-400" />
                            <span>{p.myReview.rating}.0 리뷰 작성됨</span>
                          </div>
                        ) : (
                          <Button
                            variant="outline" size="sm"
                            className="rounded-xl gap-1.5"
                            onClick={() => setReviewTarget(p)}
                          >
                            <MessageSquare className="w-3.5 h-3.5" />
                            리뷰 쓰기
                          </Button>
                        )}
                        <Button
                          variant="outline" size="sm"
                          className="rounded-xl gap-1.5"
                          onClick={() => setAddTarget(p)}
                        >
                          <PanelTop className="w-3.5 h-3.5" />
                          워크스페이스 추가
                        </Button>
                      </div>
                    </div>
                  ))}
                  {activePurchases.length === 0 && (
                    <div className="text-center py-12 text-muted-foreground">
                      <ShoppingBag className="w-10 h-10 mx-auto mb-3 opacity-30" />
                      <p className="text-sm">이용 중인 구매 내역이 없습니다.</p>
                    </div>
                  )}
                </div>
              )}

              {/* Pending — confirm or cancel */}
              {purchaseTab === "pending" && (
                <div className="space-y-3">
                  {pendingPurchases.map((p) => {
                    const remaining = p.deadline ? getRemainingDays(p.deadline) : 0
                    const isUrgent = remaining <= 1
                    return (
                      <div key={p.id} className={`border rounded-2xl p-5 space-y-3 ${isUrgent ? "border-amber-300 bg-amber-50/30" : ""}`}>
                        <div className="flex items-start gap-4">
                          <div className="w-10 h-10 rounded-xl bg-muted flex items-center justify-center flex-shrink-0">
                            <Package className="w-5 h-5 text-muted-foreground" />
                          </div>
                          <div className="flex-1">
                            <p className="font-medium text-sm">{p.name}</p>
                            <p className="text-xs text-muted-foreground">{p.creator} · {p.purchasedAt}</p>
                          </div>
                          <span className="text-sm font-bold flex-shrink-0">{p.price.toLocaleString()}원</span>
                        </div>
                        <div className={`flex items-center justify-between px-4 py-2.5 rounded-xl ${isUrgent ? "bg-amber-100" : "bg-secondary"}`}>
                          <div className="flex items-center gap-2">
                            <Clock className={`w-4 h-4 ${isUrgent ? "text-amber-600" : "text-muted-foreground"}`} />
                            <p className={`text-xs font-medium ${isUrgent ? "text-amber-700" : "text-muted-foreground"}`}>
                              구매 확정 마감: {remaining === 0 ? "오늘까지" : `${remaining}일 후`}
                            </p>
                          </div>
                          <p className="text-[11px] text-muted-foreground">미확정 시 자동 취소</p>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            className="flex-1 rounded-xl gap-1.5 text-red-600 border-red-200 hover:bg-red-50"
                            onClick={() => setCancelTarget(p)}
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                            취소 및 환불
                          </Button>
                          <Button
                            size="sm"
                            className="flex-1 rounded-xl gap-1.5"
                            onClick={() => handleConfirmPurchase(p.id)}
                          >
                            <CheckCircle className="w-3.5 h-3.5" />
                            구매 확정
                          </Button>
                        </div>
                      </div>
                    )
                  })}
                  {pendingPurchases.length === 0 && (
                    <div className="text-center py-12 text-muted-foreground">
                      <CheckCircle className="w-10 h-10 mx-auto mb-3 opacity-30" />
                      <p className="text-sm">확정 대기 중인 구매가 없습니다.</p>
                    </div>
                  )}
                </div>
              )}

              {/* Cancelled */}
              {purchaseTab === "cancelled" && (
                <div className="space-y-3">
                  {cancelledPurchases.map((p) => (
                    <div key={p.id} className="border rounded-2xl p-5 flex items-center gap-4 opacity-70">
                      <div className="w-10 h-10 rounded-xl bg-muted flex items-center justify-center flex-shrink-0">
                        <Package className="w-5 h-5 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm line-through text-muted-foreground">{p.name}</p>
                        <p className="text-xs text-muted-foreground">{p.creator} · {p.purchasedAt}</p>
                      </div>
                      <span className="text-xs px-2.5 py-0.5 rounded-xl font-medium bg-red-50 text-red-600 flex-shrink-0">
                        취소됨 · 환불 처리 중
                      </span>
                    </div>
                  ))}
                  {cancelledPurchases.length === 0 && (
                    <div className="text-center py-12 text-muted-foreground">
                      <RefreshCw className="w-10 h-10 mx-auto mb-3 opacity-30" />
                      <p className="text-sm">취소된 구매 내역이 없습니다.</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── Settings ── */}
          {tab === "settings" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold mb-1">설정</h2>
                <p className="text-sm text-muted-foreground">계정 및 알림 설정을 관리하세요.</p>
              </div>
              <div className="border rounded-2xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold">프로필 정보</h3>
                  <button onClick={() => setEditingProfile(!editingProfile)} className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1">
                    <Edit3 className="w-3 h-3" /> {editingProfile ? "취소" : "편집"}
                  </button>
                </div>
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">이름 / 닉네임</label>
                    <Input value={profileName} onChange={(e) => setProfileName(e.target.value)} disabled={!editingProfile} className="rounded-xl h-9 text-sm" />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">이메일</label>
                    <Input value={profileEmail} onChange={(e) => setProfileEmail(e.target.value)} disabled={!editingProfile} className="rounded-xl h-9 text-sm" />
                  </div>
                  {editingProfile && <Button size="sm" className="rounded-xl" onClick={handleSaveProfile}>저장하기</Button>}
                </div>
              </div>
              <div className="border rounded-2xl p-5 space-y-4">
                <h3 className="text-sm font-semibold flex items-center gap-2"><Bell className="w-4 h-4" /> 알림 설정</h3>
                {[
                  { key: "notif_email", label: "이메일 알림", desc: "판매 및 리뷰 알림을 이메일로 받습니다", value: notifEmail, set: setNotifEmail },
                  { key: "notif_sale", label: "판매 알림",   desc: "내 템플릿이 판매될 때 알림을 받습니다", value: notifSale,  set: setNotifSale },
                  { key: "notif_review", label: "리뷰 알림",   desc: "새 리뷰가 달릴 때 알림을 받습니다",     value: notifReview, set: setNotifReview },
                ].map(({ key, label, desc, value, set }) => (
                  <div key={label} className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">{label}</p>
                      <p className="text-xs text-muted-foreground">{desc}</p>
                    </div>
                    <button onClick={async () => {
                      const newValue = !value
                      set(newValue)
                      try {
                        await api.updateProfile({ [key]: newValue })
                      } catch (error) {
                        console.error("알림 설정 저장 실패:", error)
                        set(value) // Revert on error
                      }
                    }}>
                      {value ? <ToggleRight className="w-8 h-8 text-primary" /> : <ToggleLeft className="w-8 h-8 text-muted-foreground" />}
                    </button>
                  </div>
                ))}
              </div>
              <div className="border rounded-2xl p-5 space-y-4">
                <h3 className="text-sm font-semibold flex items-center gap-2"><Monitor className="w-4 h-4" /> 로컬 에이전트</h3>
                <p className="text-xs text-muted-foreground">워크플로우를 실행하려면 로컬 에이전트를 설치하고 연결하세요.</p>
                <AgentSetupGuide />
              </div>
              <div className="border rounded-2xl p-5 space-y-3">
                <h3 className="text-sm font-semibold flex items-center gap-2"><CreditCard className="w-4 h-4" /> 정산 계좌</h3>
                <div className="flex items-center gap-3 p-3 bg-muted/50 rounded-xl">
                  <CreditCard className="w-5 h-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">카카오뱅크 3333-01-1234567</p>
                    <p className="text-xs text-muted-foreground">홍길동</p>
                  </div>
                  <button className="ml-auto text-xs text-muted-foreground hover:text-foreground">변경</button>
                </div>
                <p className="text-xs text-muted-foreground">수익은 매월 15일에 정산됩니다. 수수료 20% 차감 후 지급됩니다.</p>
              </div>
              <div className="border border-red-200 rounded-2xl p-5 space-y-3">
                <h3 className="text-sm font-semibold text-red-600">위험 구역</h3>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm">계정 삭제</p>
                    <p className="text-xs text-muted-foreground">모든 데이터가 영구적으로 삭제됩니다.</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="rounded-xl border-red-200 text-red-600 hover:bg-red-50"
                    onClick={() => { setShowDeleteAccount(true); setDeleteAccountStep(1) }}
                  >
                    탈퇴하기
                  </Button>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>

      {/* Dialogs */}
      {deleteTarget && (
        <DeleteConfirmDialog
          name={deleteTarget.name}
          step={deleteStep}
          onStep={() => setDeleteStep(2)}
          onCancel={() => { setDeleteTarget(null); setDeleteStep(1) }}
          onConfirm={handleDeleteTemplate}
        />
      )}
      {reviewTarget && (
        <ReviewModal
          purchase={reviewTarget}
          onClose={() => setReviewTarget(null)}
          onSubmit={handleSubmitReview}
        />
      )}
      {editTarget && (
        <EditTemplateModal
          template={editTarget}
          onClose={() => setEditTarget(null)}
          onSave={handleSaveTemplate}
        />
      )}
      {cancelTarget && (
        <CancelConfirmDialog
          purchase={cancelTarget}
          onClose={() => setCancelTarget(null)}
          onConfirm={handleCancelPurchase}
        />
      )}
      {addTarget && (
        <AddToWorkspaceModal
          purchase={addTarget}
          onClose={() => setAddTarget(null)}
          onConfirm={(sheetName) => {
            onAddToWorkspace?.(addTarget, sheetName)
            setAddTarget(null)
          }}
        />
      )}
      {showDeleteAccount && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => { setShowDeleteAccount(false); setDeleteAccountStep(1) }} />
          <div className="relative bg-background rounded-3xl shadow-2xl p-6 w-full max-w-sm mx-4 space-y-4">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 ${deleteAccountStep === 1 ? "bg-amber-100" : "bg-red-100"}`}>
                <AlertTriangle className={`w-5 h-5 ${deleteAccountStep === 1 ? "text-amber-600" : "text-red-600"}`} />
              </div>
              <div>
                <h3 className="font-bold text-sm">{deleteAccountStep === 1 ? "정말 탈퇴하시겠어요?" : "최종 확인 - 복구 불가"}</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {deleteAccountStep === 1
                    ? "탈퇴 시 모든 데이터가 삭제됩니다."
                    : "삭제하면 계정을 복구할 수 없습니다."}
                </p>
              </div>
            </div>
            {deleteAccountStep === 2 && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3">
                <p className="text-xs text-red-700 font-medium">이 작업은 되돌릴 수 없습니다.</p>
                <p className="text-xs text-red-600 mt-1">• 모든 템플릿이 삭제됩니다</p>
                <p className="text-xs text-red-600">• 모든 구매 내역이 삭제됩니다</p>
                <p className="text-xs text-red-600">• 워크스페이스가 삭제됩니다</p>
              </div>
            )}
            <div className="flex gap-2 pt-1">
              <Button
                variant="outline"
                className="flex-1 rounded-xl"
                onClick={() => { setShowDeleteAccount(false); setDeleteAccountStep(1) }}
              >
                취소
              </Button>
              <Button
                className={`flex-1 rounded-xl ${deleteAccountStep === 2 ? "bg-red-600 hover:bg-red-700 text-white" : ""}`}
                onClick={async () => {
                  if (deleteAccountStep === 1) {
                    setDeleteAccountStep(2)
                  } else {
                    try {
                      await api.deleteAccount()
                      logout()
                    } catch (error) {
                      console.error("계정 삭제 실패:", error)
                    }
                  }
                }}
              >
                {deleteAccountStep === 1 ? "계속 진행" : "완전히 탈퇴"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
