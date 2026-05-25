"use client"

import { Star, Download, BadgeCheck, ShoppingCart } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { AutomationItem } from "@/data/marketplace"

interface MarketplaceCardProps {
  item: AutomationItem
  onPurchase?: (item: AutomationItem) => void
  onClick?: (item: AutomationItem) => void
}

function BlockPreview({ colors }: { colors: string[] }) {
  // 최대 4개만 표시
  const displayColors = colors.slice(0, 4)
  const remainingCount = colors.length - 4

  return (
    <div className="flex flex-col gap-1.5 p-3 h-full justify-center">
      {displayColors.map((color, i) => (
        <div
          key={i}
          className="h-5 rounded-lg opacity-90"
          style={{
            backgroundColor: color,
            width: `${90 - i * 10}%`,
            marginLeft: i % 2 === 1 ? "8%" : "0",
          }}
        />
      ))}
      {remainingCount > 0 && (
        <div className="text-[10px] text-muted-foreground text-center mt-1">
          +{remainingCount}개 블록
        </div>
      )}
    </div>
  )
}

export function MarketplaceCard({ item, onPurchase, onClick }: MarketplaceCardProps) {
  const isFree = item.price === 0

  return (
    <div
      className="group bg-card border rounded-2xl overflow-hidden hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 flex flex-col cursor-pointer"
      onClick={() => onClick?.(item)}
    >
      {/* Thumbnail */}
      <div className="bg-muted/50 border-b h-32 relative">
        <BlockPreview colors={item.blockColors} />
        <div className="absolute top-2 right-2 flex gap-1.5">
          {item.featured && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-400 text-amber-950">
              인기
            </span>
          )}
          {isFree && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-green-500 text-white">
              무료
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-4 flex flex-col gap-3 flex-1">
        <div className="flex-1">
          <div className="flex items-start justify-between gap-2 mb-1">
            <h3 className="font-semibold text-sm text-foreground leading-tight line-clamp-2 text-pretty">
              {item.title}
            </h3>
          </div>
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {item.description}
          </p>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-1">
          {item.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-[10px] px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Stats */}
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
            <span className="font-medium text-foreground">{item.rating}</span>
            <span>({item.reviews})</span>
          </span>
          <span className="flex items-center gap-1">
            <Download className="w-3 h-3" />
            {item.downloads.toLocaleString()}
          </span>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-1 border-t">
          <div className="flex items-center gap-1.5">
            <div className="w-5 h-5 rounded-full bg-primary flex items-center justify-center text-[10px] font-bold text-primary-foreground">
              {item.creatorAvatar}
            </div>
            <span className="text-xs text-muted-foreground flex items-center gap-0.5">
              {item.creator}
              {item.verified && <BadgeCheck className="w-3 h-3 text-blue-500" />}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-foreground">
              {isFree ? "무료" : `${item.price.toLocaleString()}원`}
            </span>
            <Button
              size="sm"
              className="h-7 px-2.5 rounded-xl text-xs gap-1"
              onClick={(e) => { e.stopPropagation(); onPurchase?.(item) }}
            >
              <ShoppingCart className="w-3 h-3" />
              {isFree ? "무료 받기" : "구매하기"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
