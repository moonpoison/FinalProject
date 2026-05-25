"use client"

import { useState, useEffect } from "react"
import {
  Star,
  Download,
  BadgeCheck,
  ArrowDownToLine,
  X,
  ShieldCheck,
  Zap,
  Clock,
  Tag,
  ChevronRight,
  ExternalLink,
  Loader2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import type { AutomationItem } from "@/data/marketplace"

interface MarketplaceDetailProps {
  item: AutomationItem | null
  onClose: () => void
  onImport: (item: AutomationItem) => void
  imported: boolean
}

interface ReviewData {
  id: string
  user_name: string
  rating: number
  text: string
  created_at: string
}

function BlockPreviewLarge({ colors }: { colors: string[] }) {
  return (
    <div className="flex flex-col gap-2 p-4">
      {colors.map((color, i) => (
        <div key={i} className="flex items-center gap-2">
          <div
            className="h-8 rounded-xl flex items-center px-3"
            style={{
              backgroundColor: color,
              width: `${90 - i * 6}%`,
              marginLeft: i % 2 === 1 ? "8%" : "0",
              opacity: 0.9,
            }}
          >
            <div className="w-2 h-2 rounded-full bg-white/60 mr-2" />
            <div className="h-1.5 rounded-full bg-white/40 flex-1" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function MarketplaceDetail({ item, onClose, onImport, imported }: MarketplaceDetailProps) {
  const [reviews, setReviews] = useState<ReviewData[]>([])
  const [isLoadingReviews, setIsLoadingReviews] = useState(false)

  useEffect(() => {
    if (item) {
      setIsLoadingReviews(true)
      api.getItemReviews(item.id)
        .then((data) => setReviews(data))
        .catch(() => setReviews([]))
        .finally(() => setIsLoadingReviews(false))
    }
  }, [item])
  if (!item) return null

  const isFree = item.price === 0

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 z-40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Slide-over panel */}
      <div className="fixed right-0 top-0 h-full w-[480px] max-w-full bg-background border-l shadow-2xl z-50 flex flex-col overflow-hidden animate-in slide-in-from-right duration-300">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>마켓플레이스</span>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="text-foreground font-medium line-clamp-1">{item.title}</span>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-xl hover:bg-secondary flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto">

          {/* Block preview */}
          <div className="bg-muted/40 border-b">
            <BlockPreviewLarge colors={item.blockColors} />
          </div>

          <div className="p-6 space-y-6">

            {/* Title & badges */}
            <div>
              <div className="flex items-start gap-2 mb-2">
                {item.featured && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-400 text-amber-950 flex-shrink-0">
                    인기
                  </span>
                )}
                {isFree && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-green-500 text-white flex-shrink-0">
                    무료
                  </span>
                )}
              </div>
              <h2 className="text-xl font-bold text-foreground leading-tight text-pretty mb-2">
                {item.title}
              </h2>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {item.description}
              </p>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-secondary/60 rounded-2xl p-3 text-center">
                <div className="flex items-center justify-center gap-1 mb-1">
                  <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                  <span className="font-bold text-foreground">{item.rating}</span>
                </div>
                <p className="text-[11px] text-muted-foreground">{item.reviews}개 리뷰</p>
              </div>
              <div className="bg-secondary/60 rounded-2xl p-3 text-center">
                <div className="font-bold text-foreground mb-1">{item.downloads.toLocaleString()}</div>
                <p className="text-[11px] text-muted-foreground flex items-center justify-center gap-0.5">
                  <Download className="w-3 h-3" /> 다운로드
                </p>
              </div>
              <div className="bg-secondary/60 rounded-2xl p-3 text-center">
                <div className="font-bold text-foreground mb-1">{item.blockColors.length}</div>
                <p className="text-[11px] text-muted-foreground flex items-center justify-center gap-0.5">
                  <Zap className="w-3 h-3" /> 블록 수
                </p>
              </div>
            </div>

            {/* Creator */}
            <div className="flex items-center gap-3 p-4 bg-secondary/40 rounded-2xl">
              <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center text-sm font-bold text-primary-foreground flex-shrink-0">
                {item.creatorAvatar}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1">
                  <span className="font-semibold text-sm text-foreground">{item.creator}</span>
                  {item.verified && <BadgeCheck className="w-4 h-4 text-blue-500" />}
                </div>
                <p className="text-xs text-muted-foreground">공식 인증 제작자</p>
              </div>
              <button className="text-xs text-primary flex items-center gap-0.5 hover:underline">
                프로필 <ExternalLink className="w-3 h-3" />
              </button>
            </div>

            {/* Features */}
            <div>
              <h3 className="text-sm font-semibold mb-3">주요 기능</h3>
              <ul className="space-y-2">
                {[
                  "드래그 앤 드롭으로 즉시 실행",
                  "결과 자동 엑셀/CSV 저장",
                  "오류 발생 시 자동 재시도",
                  "실행 로그 실시간 확인",
                ].map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <ShieldCheck className="w-4 h-4 text-green-500 flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>

            {/* Tags */}
            <div>
              <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                <Tag className="w-3.5 h-3.5" /> 태그
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {item.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-xs px-2.5 py-1 rounded-xl bg-secondary text-secondary-foreground"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            {/* Reviews */}
            <div>
              <h3 className="text-sm font-semibold mb-3">최근 리뷰</h3>
              <div className="space-y-3">
                {isLoadingReviews ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                  </div>
                ) : reviews.length === 0 ? (
                  <div className="text-center py-4 text-sm text-muted-foreground">
                    아직 리뷰가 없습니다.
                  </div>
                ) : (
                  reviews.slice(0, 5).map((r) => (
                    <div key={r.id} className="p-3 bg-secondary/40 rounded-xl">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-1">
                          {Array.from({ length: 5 }).map((_, i) => (
                            <Star
                              key={i}
                              className={`w-3 h-3 ${i < r.rating ? "fill-amber-400 text-amber-400" : "text-muted-foreground/30"}`}
                            />
                          ))}
                        </div>
                        <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                          <Clock className="w-3 h-3" /> {new Date(r.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground">{r.text}</p>
                      <p className="text-[10px] text-muted-foreground/60 mt-1">{r.user_name}</p>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>
        </div>

        {/* Sticky footer CTA */}
        <div className="flex-shrink-0 border-t p-4 bg-background">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-xs text-muted-foreground">가격</p>
              <p className="text-2xl font-bold text-foreground">
                {isFree ? "무료" : `${item.price.toLocaleString()}원`}
              </p>
            </div>
            {imported ? (
              <div className="px-6 py-2.5 rounded-2xl bg-green-500 text-white text-sm font-semibold">
                워크스페이스에 추가됨
              </div>
            ) : (
              <Button
                className="rounded-2xl px-6 h-11 gap-2 text-sm font-semibold"
                onClick={() => onImport(item)}
              >
                <ArrowDownToLine className="w-4 h-4" />
                {isFree ? "무료로 가져오기" : "구매하고 가져오기"}
              </Button>
            )}
          </div>
          <p className="text-[11px] text-muted-foreground text-center">
            가져오기 후 워크스페이스에서 바로 실행할 수 있습니다
          </p>
        </div>
      </div>
    </>
  )
}
