"use client"

import { useState, useMemo, useEffect, useCallback } from "react"
import { Search, SlidersHorizontal, TrendingUp, Sparkles, X, PlusCircle, Loader2 } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { MarketplaceCard } from "./marketplace-card"
import { MarketplaceDetail } from "./marketplace-detail"
import { SellModal } from "./sell-modal"
import { PurchaseModal } from "./purchase-modal"
import {
  type AutomationItem,
  type MarketCategory,
  type SortOption,
} from "@/data/marketplace"
import { api, type MarketplaceItemResponse } from "@/lib/api"

const CATEGORIES: MarketCategory[] = ["전체", "웹 자동화", "데이터 수집", "SNS 자동화", "업무 자동화", "쇼핑몰"]
const SORT_OPTIONS: SortOption[] = ["인기순", "최신순", "평점순", "무료"]

function apiItemToAutomationItem(item: MarketplaceItemResponse): AutomationItem {
  return {
    id: item.id,
    title: item.title,
    description: item.description,
    category: item.category as MarketCategory,
    price: item.price,
    rating: item.rating,
    reviews: item.reviews,
    downloads: item.downloads,
    creator: item.creator,
    creatorAvatar: item.creator_avatar || item.creator[0],
    tags: item.tags,
    blockColors: item.block_colors,
    featured: item.featured,
    verified: item.verified,
  }
}

interface MarketplacePageProps {
  onPurchase?: (item: AutomationItem) => void
  onCardClick?: (item: AutomationItem) => void
  onSell?: () => void
}

export function MarketplacePage({ onPurchase, onCardClick, onSell }: MarketplacePageProps) {
  const [search, setSearch] = useState("")
  const [category, setCategory] = useState<MarketCategory>("전체")
  const [sort, setSort] = useState<SortOption>("인기순")
  const [purchasedId, setPurchasedId] = useState<string | null>(null)
  const [selectedItem, setSelectedItem] = useState<AutomationItem | null>(null)
  const [purchaseTarget, setPurchaseTarget] = useState<AutomationItem | null>(null)
  const [showSellModal, setShowSellModal] = useState(false)
  const [items, setItems] = useState<AutomationItem[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const fetchItems = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await api.getMarketplaceItems({
        category: category !== "전체" ? category : undefined,
        search: search.trim() || undefined,
        sort,
      })
      setItems(response.items.map(apiItemToAutomationItem))
    } catch {
      setItems([])
    } finally {
      setIsLoading(false)
    }
  }, [category, search, sort])

  useEffect(() => {
    const debounce = setTimeout(() => {
      fetchItems()
    }, 300)
    return () => clearTimeout(debounce)
  }, [fetchItems])

  const filtered = useMemo(() => {
    return items
  }, [items])

  const featured = useMemo(() => items.filter((i) => i.featured), [items])

  const handlePurchase = (item: AutomationItem) => {
    setPurchaseTarget(item)
  }

  const handlePurchaseComplete = (item: AutomationItem) => {
    setPurchasedId(item.id)
    onPurchase?.(item)
    setTimeout(() => setPurchasedId(null), 2500)
  }

  const handleCardClick = (item: AutomationItem) => {
    if (onCardClick) {
      onCardClick(item)
    } else {
      setSelectedItem(item)
    }
  }

  return (
    <div className="h-full flex flex-col overflow-hidden bg-background">
      {/* Top bar */}
      <div className="flex-shrink-0 border-b px-6 py-4 bg-background">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="자동화를 검색하세요... (예: 네이버 수집, 인스타그램)"
                className="pl-9 h-10 rounded-2xl"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              {search && (
                <button
                  onClick={() => setSearch("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            <Button
              onClick={() => onSell ? onSell() : setShowSellModal(true)}
              variant="outline"
              className="rounded-2xl h-10 px-4 gap-2 text-sm font-medium flex-shrink-0"
            >
              <PlusCircle className="w-4 h-4" />
              판매하기
            </Button>
          </div>

          {/* Categories + sort */}
          <div className="flex items-center gap-2 flex-wrap">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategory(cat)}
                className={`px-3.5 py-1.5 rounded-xl text-sm font-medium transition-all ${
                  category === cat
                    ? "bg-foreground text-background"
                    : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                }`}
              >
                {cat}
              </button>
            ))}
            <div className="ml-auto flex items-center gap-1.5">
              <SlidersHorizontal className="w-4 h-4 text-muted-foreground" />
              {SORT_OPTIONS.map((opt) => (
                <button
                  key={opt}
                  onClick={() => setSort(opt)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                    sort === opt
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-6 py-6 space-y-8">

          {/* Featured */}
          {category === "전체" && !search && sort === "인기순" && (
            <section>
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-amber-500" />
                <h2 className="text-sm font-semibold text-foreground">이번 주 인기 자동화</h2>
              </div>
              <div className="grid grid-cols-2 gap-4">
                {featured.slice(0, 2).map((item) => (
                  <div key={item.id} className="relative">
                    {purchasedId === item.id && (
                      <div className="absolute inset-0 z-10 flex items-center justify-center bg-green-500/20 rounded-2xl border-2 border-green-500 pointer-events-none">
                        <span className="text-sm font-semibold text-green-700">구매 완료</span>
                      </div>
                    )}
                    <MarketplaceCard item={item} onPurchase={handlePurchase} onClick={handleCardClick} />
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* All / filtered */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-primary" />
              <h2 className="text-sm font-semibold text-foreground">
                {search
                  ? `"${search}" 검색 결과 ${filtered.length}개`
                  : category !== "전체"
                  ? `${category} (${filtered.length}개)`
                  : `전체 자동화 (${filtered.length}개)`}
              </h2>
            </div>

            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
                <p className="text-muted-foreground text-sm">로딩 중...</p>
              </div>
            ) : filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <p className="text-lg font-semibold text-foreground mb-2">검색 결과가 없습니다</p>
                <p className="text-muted-foreground text-sm">다른 키워드로 검색해보세요.</p>
                <Button
                  variant="outline"
                  className="mt-4 rounded-xl"
                  onClick={() => { setSearch(""); setCategory("전체") }}
                >
                  전체 보기
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                {filtered.map((item) => (
                  <div key={item.id} className="relative">
                    {purchasedId === item.id && (
                      <div className="absolute inset-0 z-10 flex items-center justify-center bg-green-500/20 rounded-2xl border-2 border-green-500 pointer-events-none">
                        <span className="text-sm font-semibold text-green-700">구매 완료</span>
                      </div>
                    )}
                    <MarketplaceCard item={item} onPurchase={handlePurchase} onClick={handleCardClick} />
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>

      {/* Detail side panel */}
      <MarketplaceDetail
        item={selectedItem}
        onClose={() => setSelectedItem(null)}
        onImport={(item) => { handlePurchase(item); setSelectedItem(null) }}
        imported={purchasedId === selectedItem?.id}
      />

      {/* Purchase modal */}
      {purchaseTarget && (
        <PurchaseModal
          item={purchaseTarget}
          onClose={() => setPurchaseTarget(null)}
          onComplete={(item) => { handlePurchaseComplete(item); setPurchaseTarget(null) }}
        />
      )}

      {/* Sell modal */}
      {showSellModal && (
        <SellModal
          onClose={() => setShowSellModal(false)}
          onSuccess={fetchItems}
        />
      )}
    </div>
  )
}
