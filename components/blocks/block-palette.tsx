"use client"

import { BLOCK_DEFINITIONS, BLOCK_CATEGORIES, type BlockCategory } from "@/types/blocks"
import { DraggableBlock } from "./draggable-block"

export function BlockPalette() {
  const categories = Object.keys(BLOCK_CATEGORIES) as BlockCategory[]

  return (
    <div id="palette-container" className="h-full overflow-y-auto p-4 space-y-6">
      <div className="text-center mb-6">
        <h2 className="text-lg font-bold text-foreground">블록 팔레트</h2>
        <p className="text-xs text-muted-foreground mt-1">
          블록을 드래그하여 작업 공간에 추가하세요
        </p>
      </div>

      {categories.map((category) => {
        const categoryInfo = BLOCK_CATEGORIES[category]
        const blocks = BLOCK_DEFINITIONS.filter((b) => b.category === category)

        return (
          <div key={category} className="space-y-2">
            <div className="flex items-center gap-2 px-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: categoryInfo.color }}
              />
              <span className="text-sm font-semibold text-foreground">
                {categoryInfo.label}
              </span>
            </div>
            <div className="space-y-2">
              {blocks.map((block) => (
                <div
                  key={block.id}
                  style={{ backgroundColor: block.color }}
                  className="rounded-2xl"
                >
                  <DraggableBlock block={block} isPalette />
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
