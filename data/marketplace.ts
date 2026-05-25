export type MarketCategory =
  | "전체"
  | "웹 자동화"
  | "데이터 수집"
  | "SNS 자동화"
  | "업무 자동화"
  | "쇼핑몰"

export type SortOption = "인기순" | "최신순" | "평점순" | "무료"

export interface AutomationItem {
  id: string
  title: string
  description: string
  category: MarketCategory
  price: number // 0 = 무료
  rating: number
  reviews: number
  downloads: number
  creator: string
  creatorAvatar: string
  tags: string[]
  blockColors: string[]
  featured?: boolean
  verified?: boolean
}

// 마켓플레이스 아이템은 API에서 로드됨
// 이 배열은 하위 호환성을 위해 빈 배열로 유지
export const MARKETPLACE_ITEMS: AutomationItem[] = []
