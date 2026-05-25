"use client"

import { useState, useEffect } from "react"
import { useAuth } from "@/contexts/auth-context"
import { useChat } from "@/contexts/chat-context"
import {
  ArrowLeft, Star, Download, Shield, User, Tag,
  Clock, Zap, CheckCircle, MessageSquare, ChevronRight,
  Share2, Bookmark, Play, MessageCircle, Loader2
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { api, type MarketplaceItemResponse } from "@/lib/api"
import type { AutomationItem } from "@/data/marketplace"
import { PurchaseModal } from "./purchase-modal"

interface MarketplaceDetailPageProps {
  item: AutomationItem
  onBack: () => void
  onPurchase: (item: AutomationItem, blocksData?: any[]) => void
}

interface ReviewData {
  id: string
  user_id: string
  user_name: string
  rating: number
  text: string
  created_at: string
}

export function MarketplaceDetailPage({ item, onBack, onPurchase }: MarketplaceDetailPageProps) {
  const { user } = useAuth()
  const { startConversation } = useChat()
  const [purchased, setPurchased] = useState(false)
  const [saved, setSaved] = useState(false)
  const [showPurchaseModal, setShowPurchaseModal] = useState(false)
  const [activeTab, setActiveTab] = useState<"overview" | "reviews" | "blocks">("overview")
  const [itemDetail, setItemDetail] = useState<MarketplaceItemResponse | null>(null)
  const [reviews, setReviews] = useState<ReviewData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  // 리뷰 작성
  const [reviewRating, setReviewRating] = useState(5)
  const [reviewText, setReviewText] = useState("")
  const [isSubmittingReview, setIsSubmittingReview] = useState(false)
  const [reviewError, setReviewError] = useState<string | null>(null)

  // 상세 데이터 로드 (blocks_data, features, usage_steps 포함)
  useEffect(() => {
    const loadDetail = async () => {
      setIsLoading(true)
      try {
        const [detail, reviewsData] = await Promise.all([
          api.getMarketplaceItem(item.id),
          api.getItemReviews(item.id)
        ])
        setItemDetail(detail)
        setReviews(reviewsData)
      } catch (err) {
        console.error("아이템 상세 로드 오류:", err)
      } finally {
        setIsLoading(false)
      }
    }
    loadDetail()
  }, [item.id])

  const isFree = item.price === 0
  const blocksData = itemDetail?.blocks_data || []
  const features = itemDetail?.features || []
  const usageSteps = itemDetail?.usage_steps || []
  const isMyItem = user?.name === item.creator  // 내 아이템인지 확인

  const handlePurchaseComplete = () => {
    setPurchased(true)
    onPurchase(item, blocksData)
    setShowPurchaseModal(false)
  }

  // 내 아이템 바로 내려받기
  const handleDirectDownload = () => {
    onPurchase(item, blocksData)
  }

  const handleChatWithSeller = () => {
    if (!user || !user.name) return
    const sellerName = item.creator || "판매자"
    const topic = item.title || "상품 문의"
    startConversation(user.id, user.name, sellerName, topic)
  }

  // 리뷰 제출
  const handleSubmitReview = async () => {
    if (!reviewText.trim() || reviewRating < 1) return
    setIsSubmittingReview(true)
    setReviewError(null)
    try {
      const newReview = await api.createReview(item.id, { rating: reviewRating, text: reviewText.trim() })
      setReviews(prev => [newReview, ...prev])
      setReviewText("")
      setReviewRating(5)
    } catch (err: any) {
      setReviewError(err.message || "리뷰 등록에 실패했습니다.")
    } finally {
      setIsSubmittingReview(false)
    }
  }

  // 이미 리뷰 작성했는지 확인
  const hasMyReview = reviews.some(r => r.user_id === user?.id)

  // 실제 리뷰 데이터 기반 별점 분포 계산
  const ratingBars = [5, 4, 3, 2, 1].map((star) => ({
    star,
    count: reviews.filter(r => r.rating === star).length
  }))
  const totalReviews = reviews.length || 1 // 0으로 나누기 방지

  return (
    <>
    {showPurchaseModal && (
      <PurchaseModal
        item={item}
        onClose={() => setShowPurchaseModal(false)}
        onComplete={handlePurchaseComplete}
      />
    )}
    <div className="h-full flex flex-col overflow-hidden bg-background">
      {/* Top nav */}
      <div className="flex-shrink-0 border-b px-6 py-3 flex items-center gap-4 bg-background">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          마켓플레이스
        </button>
        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
        <span className="text-sm font-medium text-foreground truncate max-w-xs">{item.title}</span>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setSaved(!saved)}
            className={`p-2 rounded-xl hover:bg-muted transition-colors ${saved ? "text-primary" : "text-muted-foreground"}`}
          >
            <Bookmark className={`w-4 h-4 ${saved ? "fill-primary" : ""}`} />
          </button>
          <button className="p-2 rounded-xl hover:bg-muted text-muted-foreground transition-colors">
            <Share2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">

          {/* Hero */}
          <div className="flex gap-8">
            {/* Left: main info */}
            <div className="flex-1 space-y-4">
              <div className="flex items-start gap-3">
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0 text-white font-bold text-xl"
                  style={{ backgroundColor: item.blockColors[1] ?? "#3b82f6" }}
                >
                  {item.creator[0]}
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-foreground leading-tight">{item.title}</h1>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-sm text-muted-foreground">by {item.creator}</span>
                    {item.verified && (
                      <span className="flex items-center gap-0.5 text-xs text-blue-600 font-medium">
                        <Shield className="w-3 h-3" /> 인증됨
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <p className="text-muted-foreground leading-relaxed">{item.description}</p>

              {/* Stats row */}
              <div className="flex items-center gap-6 text-sm">
                <div className="flex items-center gap-1.5">
                  <div className="flex">
                    {[1,2,3,4,5].map((s) => (
                      <Star key={s} className={`w-4 h-4 ${s <= Math.round(item.rating) ? "fill-amber-400 text-amber-400" : "text-muted-foreground/30"}`} />
                    ))}
                  </div>
                  <span className="font-semibold">{item.rating}</span>
                  <span className="text-muted-foreground">({item.reviews.toLocaleString()})</span>
                </div>
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Download className="w-4 h-4" />
                  <span>{item.downloads.toLocaleString()} 다운로드</span>
                </div>
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Tag className="w-4 h-4" />
                  <span>{item.category}</span>
                </div>
              </div>

              {/* Tags */}
              <div className="flex flex-wrap gap-2">
                {item.tags.map((tag) => (
                  <span key={tag} className="px-3 py-1 bg-secondary text-secondary-foreground text-xs rounded-xl font-medium">
                    #{tag}
                  </span>
                ))}
              </div>
            </div>

            {/* Right: purchase card */}
            <div className="w-72 flex-shrink-0">
              <div className="border rounded-2xl p-5 space-y-4 sticky top-4">
                <div className="text-center">
                  {isMyItem ? (
                    <span className="text-xl font-bold text-primary">내 자동화</span>
                  ) : isFree ? (
                    <span className="text-3xl font-bold text-green-600">무료</span>
                  ) : (
                    <div>
                      <span className="text-3xl font-bold text-foreground">{item.price.toLocaleString()}</span>
                      <span className="text-sm text-muted-foreground ml-1">원</span>
                    </div>
                  )}
                </div>

                {isMyItem ? (
                  // 내 아이템 - 바로 내려받기
                  <Button
                    className="w-full rounded-2xl h-11 font-semibold gap-2"
                    onClick={handleDirectDownload}
                  >
                    <Download className="w-4 h-4" /> 내려받기
                  </Button>
                ) : (
                  // 다른 사람 아이템 - 구매
                  <Button
                    className="w-full rounded-2xl h-11 font-semibold gap-2"
                    onClick={() => setShowPurchaseModal(true)}
                    disabled={purchased}
                    variant={purchased ? "outline" : "default"}
                  >
                    {purchased ? (
                      <><CheckCircle className="w-4 h-4 text-green-600" /> 구매 완료</>
                    ) : (
                      <><Play className="w-4 h-4" /> {isFree ? "무료로 받기" : "구매하기"}</>
                    )}
                  </Button>
                )}

                {!isMyItem && (
                  <Button
                    variant="outline"
                    className="w-full rounded-2xl h-11 font-semibold gap-2"
                    onClick={handleChatWithSeller}
                  >
                    <MessageCircle className="w-4 h-4" />
                    판매자에게 문의하기
                  </Button>
                )}

                {!isMyItem && !isFree && (
                  <p className="text-xs text-center text-muted-foreground">구매 후 3일 이내 환불 보장</p>
                )}

                <div className="space-y-2 pt-2 border-t text-sm">
                  <div className="flex justify-between text-muted-foreground">
                    <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" /> 마지막 업데이트</span>
                    <span className="text-foreground">2025.01.15</span>
                  </div>
                  <div className="flex justify-between text-muted-foreground">
                    <span className="flex items-center gap-1.5"><Zap className="w-3.5 h-3.5" /> 블록 수</span>
                    <span className="text-foreground">{blocksData.length}개</span>
                  </div>
                  <div className="flex justify-between text-muted-foreground">
                    <span className="flex items-center gap-1.5"><User className="w-3.5 h-3.5" /> 사용자</span>
                    <span className="text-foreground">{item.downloads.toLocaleString()}명</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b flex gap-0">
            {(["overview", "blocks", "reviews"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
                  activeTab === tab
                    ? "border-primary text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                {tab === "overview" ? "개요" : tab === "blocks" ? "블록 구성" : `리뷰 (${reviews.length})`}
              </button>
            ))}
          </div>

          {/* Tab content */}
          {activeTab === "overview" && (
            <div className="space-y-6">
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <>
                  <div>
                    <h2 className="text-base font-semibold mb-3">주요 기능</h2>
                    {features.length > 0 ? (
                      <ul className="space-y-2">
                        {features.map((f, i) => (
                          <li key={i} className="flex items-start gap-2.5 text-sm text-muted-foreground">
                            <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                            {f}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-muted-foreground">주요 기능 정보가 없습니다.</p>
                    )}
                  </div>
                  <div>
                    <h2 className="text-base font-semibold mb-3">사용 방법</h2>
                    {usageSteps.length > 0 ? (
                      <ol className="space-y-3">
                        {usageSteps.map((step, i) => (
                          <li key={i} className="flex items-start gap-3 text-sm">
                            <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center flex-shrink-0 font-bold">{i + 1}</span>
                            <span className="text-muted-foreground mt-0.5">{step}</span>
                          </li>
                        ))}
                      </ol>
                    ) : (
                      <p className="text-sm text-muted-foreground">사용 방법 정보가 없습니다.</p>
                    )}
                  </div>
                </>
              )}
            </div>
          )}

          {activeTab === "blocks" && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">이 자동화를 가져오면 아래 블록들이 워크스페이스에 추가됩니다.</p>
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                </div>
              ) : blocksData.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">블록 정보가 없습니다.</p>
              ) : (
                <div className="space-y-2">
                  {blocksData.map((block: any, i: number) => (
                    <div key={i} className="flex items-center gap-3 p-3 border rounded-2xl">
                      <div className="w-8 h-8 rounded-xl flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: block.color || "#6b7280" }}>
                        {i + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{block.label || block.type || "블록"}</p>
                        <p className="text-xs text-muted-foreground truncate">
                          {block.fieldValues?.url || block.fieldValues?.selector || block.fieldValues?.text || block.type || ""}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === "reviews" && (
            <div className="space-y-6">
              {/* Rating summary */}
              <div className="flex gap-8 p-5 border rounded-2xl">
                <div className="text-center">
                  <p className="text-5xl font-bold">{item.rating}</p>
                  <div className="flex justify-center mt-1">
                    {[1,2,3,4,5].map((s) => (
                      <Star key={s} className={`w-4 h-4 ${s <= Math.round(item.rating) ? "fill-amber-400 text-amber-400" : "text-muted-foreground/30"}`} />
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{reviews.length}개 리뷰</p>
                </div>
                <div className="flex-1 space-y-1.5">
                  {ratingBars.map(({ star, count }) => (
                    <div key={star} className="flex items-center gap-2 text-xs">
                      <span className="w-4 text-right">{star}</span>
                      <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-amber-400 rounded-full"
                          style={{ width: `${(count / totalReviews) * 100}%` }}
                        />
                      </div>
                      <span className="w-8 text-muted-foreground">{count}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* 리뷰 작성 폼 (구매 완료 & 아직 리뷰 안 쓴 경우) */}
              {purchased && !hasMyReview && !isMyItem && (
                <div className="border rounded-2xl p-5 space-y-4">
                  <h3 className="font-semibold text-sm">리뷰 작성</h3>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">평점:</span>
                    <div className="flex">
                      {[1,2,3,4,5].map((s) => (
                        <button
                          key={s}
                          onClick={() => setReviewRating(s)}
                          className="p-0.5"
                        >
                          <Star className={`w-6 h-6 transition-colors ${s <= reviewRating ? "fill-amber-400 text-amber-400" : "text-muted-foreground/30 hover:text-amber-300"}`} />
                        </button>
                      ))}
                    </div>
                  </div>
                  <Textarea
                    placeholder="이 자동화에 대한 솔직한 리뷰를 작성해주세요..."
                    value={reviewText}
                    onChange={(e) => setReviewText(e.target.value)}
                    className="min-h-[100px] rounded-xl resize-none"
                  />
                  {reviewError && (
                    <p className="text-sm text-red-500">{reviewError}</p>
                  )}
                  <Button
                    onClick={handleSubmitReview}
                    disabled={!reviewText.trim() || isSubmittingReview}
                    className="rounded-xl"
                  >
                    {isSubmittingReview ? "등록 중..." : "리뷰 등록"}
                  </Button>
                </div>
              )}

              {/* Review list */}
              <div className="space-y-4">
                {reviews.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">아직 리뷰가 없습니다.</p>
                ) : (
                  reviews.map((review) => (
                    <div key={review.id} className="border rounded-2xl p-4 space-y-2">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-sm font-medium">
                          {review.user_name[0]}
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium">{review.user_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(review.created_at).toLocaleDateString('ko-KR')}
                          </p>
                        </div>
                        <div className="flex">
                          {[1,2,3,4,5].map((s) => (
                            <Star key={s} className={`w-3.5 h-3.5 ${s <= review.rating ? "fill-amber-400 text-amber-400" : "text-muted-foreground/30"}`} />
                          ))}
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground leading-relaxed">{review.text}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
    </>
  )
}
