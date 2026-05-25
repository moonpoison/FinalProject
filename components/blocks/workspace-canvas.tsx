"use client"

import { useDroppable } from "@dnd-kit/core"
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { WorkspaceBlock } from "./workspace-block"
import type { WorkspaceBlock as WorkspaceBlockType } from "@/types/blocks"
import { Layers } from "lucide-react"
import { useRef, useEffect } from "react"

interface WorkspaceCanvasProps {
  blocks: WorkspaceBlockType[]
  onUpdateBlock: (instanceId: string, fieldValues: Record<string, string | number>) => void
  onDeleteBlock: (instanceId: string) => void
}

export function WorkspaceCanvas({
  blocks,
  onUpdateBlock,
  onDeleteBlock,
}: WorkspaceCanvasProps) {
  const { setNodeRef, isOver } = useDroppable({ id: "workspace" })
  const scrollRef = useRef<HTMLDivElement>(null)
  const prevLengthRef = useRef(blocks.length)

  useEffect(() => {
    if (blocks.length > prevLengthRef.current && scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      })
    }
    prevLengthRef.current = blocks.length
  }, [blocks.length])

  return (
    <div
      ref={(node) => {
        setNodeRef(node)
        ;(scrollRef as React.MutableRefObject<HTMLDivElement | null>).current = node
      }}
      className={`
        h-full overflow-y-auto p-6
        bg-[radial-gradient(circle,_var(--tw-gradient-stops))]
        from-muted/30 via-background to-background
        transition-colors duration-200
        ${isOver ? "bg-primary/5" : ""}
      `}
      style={{
        backgroundImage: `
          radial-gradient(circle at 1px 1px, var(--border) 1px, transparent 0)
        `,
        backgroundSize: "24px 24px",
      }}
    >
      {blocks.length === 0 ? (
        <div className="h-full flex flex-col items-center justify-center text-center">
          <div className="w-20 h-20 rounded-3xl bg-muted/50 flex items-center justify-center mb-4">
            <Layers className="w-10 h-10 text-muted-foreground/50" />
          </div>
          <h3 className="text-lg font-semibold text-foreground/70 mb-2">
            작업 공간이 비어있습니다
          </h3>
          <p className="text-sm text-muted-foreground max-w-xs">
            왼쪽에서 블록을 드래그하여 여기에 놓거나,
            <br />
            AI에게 자동화 작업을 설명해보세요
          </p>
        </div>
      ) : (
          <div className="max-w-md mx-auto">
          <SortableContext
            items={blocks.map((b) => b.instanceId)}
            strategy={verticalListSortingStrategy}
          >
            {blocks.map((block, index) => (
              <WorkspaceBlock
                key={block.instanceId}
                block={block}
                index={index}
                isLast={index === blocks.length - 1}
                onUpdate={onUpdateBlock}
                onDelete={onDeleteBlock}
              />
            ))}
          </SortableContext>
        </div>
      )}
    </div>
  )
}
