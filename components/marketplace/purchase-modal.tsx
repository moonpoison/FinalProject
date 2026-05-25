"use client"

import { useState } from "react"
import {
  ShoppingCart, X, CreditCard, Wallet, Building2,
  CheckCircle2, Lock, ChevronRight, Star, Download, Shield,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { useAuth } from "@/contexts/auth-context"
import type { AutomationItem } from "@/data/marketplace"

type Step = "confirm" | "payment" | "done"
type PaymentMethod = "kakao"

interface PurchaseModalProps {
  item: AutomationItem
  onClose: () => void
  onComplete: (item: AutomationItem) => void
}

const PAYMENT_METHODS: { id: PaymentMethod; label: string; desc: string; icon: React.ElementType }[] = [
  { id: "kakao", label: "카카오페이", desc: "간편결제", icon: Wallet },
]

// PortOne 채널키
const PORTONE_CHANNEL_KEY = "channel-key-3994b36c-d73f-4ddb-b528-3745ff201a6c"
const PORTONE_STORE_ID = process.env.NEXT_PUBLIC_PORTONE_STORE_ID || ""

export function PurchaseModal({ item, onClose, onComplete }: PurchaseModalProps) {
  const { user } = useAuth()
  const [step, setStep] = useState<Step>("confirm")
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("kakao")
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isFree = item.price === 0
  const fee = isFree ? 0 : Math.round(item.price * 0.1)
  const total = item.price + fee

  // PortOne 결제 요청
  const handlePay = async () => {
    setIsProcessing(true)
    setError(null)

    try {
      // 무료 상품은 바로 구매 처리
      if (isFree) {
        await api.purchaseItem(item.id)
        setStep("done")
        return
      }

      // PortOne SDK 동적 로드
      if (!PORTONE_STORE_ID) {
        throw new Error("결제 시스템이 설정되지 않았습니다. 관리자에게 문의하세요.")
      }
      const PortOne = await import("@portone/browser-sdk/v2")

      // 결제 요청 파라미터
      const paymentId = `payment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

      // 결제 방식 매핑 (카카오페이만 사용)
      const payMethodMap: Record<PaymentMethod, "EASY_PAY"> = {
        kakao: "EASY_PAY"
      }

      const response = await PortOne.requestPayment({
        storeId: PORTONE_STORE_ID,
        channelKey: PORTONE_CHANNEL_KEY,
        paymentId,
        orderName: item.title,
        totalAmount: total,
        currency: "CURRENCY_KRW",
        payMethod: payMethodMap[paymentMethod] as any,
        customer: {
          fullName: user?.name || "고객",
          email: user?.email || undefined,
        },
        customData: {
          itemId: item.id,
          buyerId: user?.id
        }
      })

      // 결제 결과 확인
      if (response?.code != null) {
        // 결제 실패 또는 취소
        throw new Error(response.message || "결제가 취소되었습니다.")
      }

      // 결제 성공 - 백엔드에서 검증 및 구매 처리
      await api.verifyPayment(paymentId, item.id, total)

      setStep("done")
    } catch (err: any) {
      console.error("결제 오류:", err)
      setError(err.message || "결제 중 오류가 발생했습니다.")
    } finally {
      setIsProcessing(false)
    }
  }

  const handleDone = () => {
    onComplete(item)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={step !== "done" ? onClose : undefined} />
      <div className="relative bg-background rounded-3xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center">
              <ShoppingCart className="w-4 h-4 text-primary" />
            </div>
            <h2 className="font-bold text-base">
              {step === "confirm" ? "구매 확인" : step === "payment" ? "결제 수단" : "구매 완료"}
            </h2>
          </div>
          {step !== "done" && (
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-xl hover:bg-secondary flex items-center justify-center text-muted-foreground"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Step indicator */}
        {!isFree && (
          <div className="flex items-center gap-1 px-6 py-3 bg-muted/30">
            {(["confirm", "payment", "done"] as Step[]).map((s, i) => (
              <div key={s} className="flex items-center gap-1">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-colors ${
                  step === s
                    ? "bg-primary text-primary-foreground"
                    : (["confirm", "payment", "done"] as Step[]).indexOf(step) > i
                    ? "bg-primary/20 text-primary"
                    : "bg-muted text-muted-foreground"
                }`}>
                  {i + 1}
                </div>
                {i < 2 && <div className="w-6 h-px bg-border" />}
              </div>
            ))}
            <span className="ml-2 text-xs text-muted-foreground">
              {step === "confirm" ? "상품 확인" : step === "payment" ? "결제" : "완료"}
            </span>
          </div>
        )}

        <div className="px-6 py-5 space-y-4">

          {/* ── Step 1: Confirm ── */}
          {step === "confirm" && (
            <>
              {/* Product info */}
              <div className="rounded-2xl border bg-muted/30 p-4 space-y-3">
                <div className="flex gap-3">
                  <div className="w-12 h-12 rounded-xl bg-muted flex flex-col gap-1 p-1.5 overflow-hidden flex-shrink-0">
                    {item.blockColors.slice(0, 4).map((c, i) => (
                      <div key={i} className="h-1.5 rounded-sm" style={{ backgroundColor: c, width: `${80 - i * 15}%` }} />
                    ))}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm leading-snug line-clamp-2">{item.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{item.creator}</p>
                    <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                      <span className="flex items-center gap-0.5">
                        <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                        {item.rating}
                      </span>
                      <span className="flex items-center gap-0.5">
                        <Download className="w-3 h-3" />
                        {item.downloads.toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Price breakdown */}
              {!isFree && (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between text-muted-foreground">
                    <span>상품 금액</span>
                    <span>{item.price.toLocaleString()}원</span>
                  </div>
                  <div className="flex justify-between text-muted-foreground">
                    <span>수수료 (10%)</span>
                    <span>{fee.toLocaleString()}원</span>
                  </div>
                  <div className="border-t pt-2 flex justify-between font-bold text-base">
                    <span>총 결제금액</span>
                    <span className="text-primary">{total.toLocaleString()}원</span>
                  </div>
                </div>
              )}

              {/* Trust badges */}
              <div className="flex items-center gap-2 py-2 px-3 rounded-xl bg-green-500/5 border border-green-500/20">
                <Shield className="w-4 h-4 text-green-600 flex-shrink-0" />
                <p className="text-xs text-green-700">
                  구매 후 3일 이내 미사용 시 100% 환불 보장
                </p>
              </div>

              <Button
                className="w-full rounded-2xl h-11 font-semibold gap-2"
                onClick={() => isFree ? handlePay() : setStep("payment")}
              >
                {isFree ? (
                  <><CheckCircle2 className="w-4 h-4" /> 무료로 받기</>
                ) : (
                  <><ChevronRight className="w-4 h-4" /> 결제 수단 선택</>
                )}
              </Button>
            </>
          )}

          {/* ── Step 2: Payment ── */}
          {step === "payment" && (
            <>
              {/* Methods */}
              <div className="space-y-2">
                {PAYMENT_METHODS.map(({ id, label, desc, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => setPaymentMethod(id)}
                    className={`w-full flex items-center gap-3 p-3.5 rounded-2xl border-2 transition-all text-left ${
                      paymentMethod === id
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-muted-foreground/30"
                    }`}
                  >
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${
                      paymentMethod === id ? "bg-primary text-primary-foreground" : "bg-muted"
                    }`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{label}</p>
                      <p className="text-xs text-muted-foreground">{desc}</p>
                    </div>
                    <div className={`w-4 h-4 rounded-full border-2 flex-shrink-0 ${
                      paymentMethod === id ? "border-primary bg-primary" : "border-muted-foreground/40"
                    }`} />
                  </button>
                ))}
              </div>

              {/* 결제 안내 */}
              <div className="text-xs text-muted-foreground text-center py-2">
                결제 버튼을 누르면 카카오페이 창이 열립니다
              </div>

              {/* Error message */}
              {error && (
                <div className="p-3 rounded-xl bg-red-500/10 text-red-600 text-sm">
                  {error}
                </div>
              )}

              {/* Total */}
              <div className="flex justify-between items-center py-3 border-t font-bold">
                <span className="text-sm">총 결제금액</span>
                <span className="text-primary">{total.toLocaleString()}원</span>
              </div>

              <div className="flex gap-2">
                <Button variant="outline" className="flex-1 rounded-2xl" onClick={() => setStep("confirm")}>
                  이전
                </Button>
                <Button
                  className="flex-1 rounded-2xl h-11 font-semibold gap-2"
                  onClick={handlePay}
                  disabled={isProcessing}
                >
                  {isProcessing ? (
                    <><Lock className="w-4 h-4 animate-pulse" /> 결제 중...</>
                  ) : (
                    <><Lock className="w-4 h-4" /> {total.toLocaleString()}원 결제</>
                  )}
                </Button>
              </div>
            </>
          )}

          {/* ── Step 3: Done ── */}
          {step === "done" && (
            <div className="flex flex-col items-center text-center py-4 space-y-4">
              <div className="w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center">
                <CheckCircle2 className="w-8 h-8 text-green-500" />
              </div>
              <div>
                <p className="font-bold text-base mb-1">구매 완료!</p>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  <span className="font-medium text-foreground">{item.title}</span>을<br />
                  성공적으로 구매했습니다.
                </p>
              </div>
              <div className="w-full rounded-2xl bg-muted/50 p-3 text-xs text-muted-foreground text-left space-y-1">
                <p>마이페이지 &gt; 구매 목록에서 확인할 수 있습니다.</p>
                <p>구매 확정 전 3일 이내에 환불 요청이 가능합니다.</p>
              </div>
              <Button className="w-full rounded-2xl h-11 font-semibold" onClick={handleDone}>
                확인
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
