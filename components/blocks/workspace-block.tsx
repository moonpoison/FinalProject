"use client"

import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import {
  Play, Globe, ArrowRight, ArrowLeft, ArrowRightCircle,
  MousePointer, MousePointer2, MousePointerClick,
  Keyboard, Command, Zap, Eraser,
  Download, FileSpreadsheet, FileText, FileInput,
  Clock, Repeat, GitBranch,
  GripVertical, Trash2, ChevronDown, ChevronUp,
  CalendarClock, RefreshCw, MoveVertical, Loader,
  ScanSearch, Camera, PanelTopOpen, XCircle, LayoutGrid, Frame,
  Scan, Hand, List, CheckSquare, Upload,
  TextCursor, Rows3, CodeXml,
  Variable, Mail, MessageSquare, ListOrdered,
  Octagon, SquareX, Terminal, ShieldAlert,
  Globe2, ListTree, Braces, Cookie, KeyRound,
  Code, X,
} from "lucide-react"
import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import type { WorkspaceBlock as WorkspaceBlockType } from "@/types/blocks"

const iconMap: Record<string, React.ElementType> = {
  play: Play,
  globe: Globe,
  "arrow-right": ArrowRight,
  "arrow-left": ArrowLeft,
  "arrow-right-circle": ArrowRightCircle,
  "mouse-pointer": MousePointer,
  "mouse-pointer-2": MousePointer2,
  "mouse-pointer-click": MousePointerClick,
  keyboard: Keyboard,
  command: Command,
  zap: Zap,
  eraser: Eraser,
  download: Download,
  "file-spreadsheet": FileSpreadsheet,
  "file-text": FileText,
  "file-input": FileInput,
  clock: Clock,
  repeat: Repeat,
  "git-branch": GitBranch,
  "calendar-clock": CalendarClock,
  "refresh-cw": RefreshCw,
  "move-vertical": MoveVertical,
  loader: Loader,
  "scan-search": ScanSearch,
  camera: Camera,
  "panel-top-open": PanelTopOpen,
  "x-circle": XCircle,
  "layout-grid": LayoutGrid,
  frame: Frame,
  scan: Scan,
  hand: Hand,
  list: List,
  "check-square": CheckSquare,
  upload: Upload,
  "text-cursor": TextCursor,
  rows: Rows3,
  "code-xml": CodeXml,
  variable: Variable,
  mail: Mail,
  "message-square": MessageSquare,
  "list-ordered": ListOrdered,
  octagon: Octagon,
  "square-x": SquareX,
  terminal: Terminal,
  "shield-alert": ShieldAlert,
  "globe-2": Globe2,
  "list-tree": ListTree,
  braces: Braces,
  cookie: Cookie,
  "key-round": KeyRound,
  code: Code,
}

interface WorkspaceBlockProps {
  block: WorkspaceBlockType
  isLast: boolean
  index: number
  onUpdate: (instanceId: string, fieldValues: Record<string, string | number>) => void
  onDelete: (instanceId: string) => void
}

export function WorkspaceBlock({ block, isLast, index, onUpdate, onDelete }: WorkspaceBlockProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  const [isCodeModalOpen, setIsCodeModalOpen] = useState(false)
  const [tempCode, setTempCode] = useState("")

  const isCodeBlock = block.id === "custom-code"

  const openCodeModal = () => {
    setTempCode((block.fieldValues?.code as string) || "")
    setIsCodeModalOpen(true)
  }

  const saveCodeAndClose = () => {
    onUpdate(block.instanceId, { ...block.fieldValues, code: tempCode })
    setIsCodeModalOpen(false)
  }

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: block.instanceId })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 1000 : undefined,
  }

  const Icon = iconMap[block.icon] || Play

  const handleFieldChange = (fieldName: string, value: string | number) => {
    onUpdate(block.instanceId, { ...block.fieldValues, [fieldName]: value })
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex flex-col items-center"
    >
      {/* Step Badge + Group Badge */}
      <div className="flex items-center gap-2 mb-2 self-start ml-4 flex-wrap">
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-sm"
          style={{ backgroundColor: block.color }}
        >
          {index + 1}
        </div>
        <span className="text-xs font-medium text-muted-foreground tracking-wide uppercase">
          {block.category === "start" ? "트리거" :
           block.category === "browser" ? "브라우저" :
           block.category === "tab" ? "탭/창" :
           block.category === "action" ? "마우스" :
           block.category === "keyboard" ? "키보드" :
           block.category === "data" ? "데이터" :
           block.category === "api" ? "API" : "제어"}
        </span>
        {block.groupLabel && (
          <span
            className="text-[10px] font-semibold px-2 py-0.5 rounded-full text-white"
            style={{ backgroundColor: block.groupColor ?? block.color }}
          >
            {block.groupLabel}
          </span>
        )}
      </div>

      {/* Block Card */}
      <div
        className={`
          w-full rounded-2xl overflow-hidden transition-all duration-200
          border-2 bg-background
          ${isDragging ? "opacity-60 scale-95 shadow-2xl rotate-1" : "shadow-md hover:shadow-lg"}
        `}
        style={{
          borderColor: `${block.color}55`,
          boxShadow: isDragging ? `0 20px 40px ${block.color}40` : `0 2px 12px ${block.color}20`,
        }}
      >
        {/* Colored top bar */}
        <div
          className="h-1 w-full"
          style={{ backgroundColor: block.color }}
        />

        {/* Header row */}
        <div
          className="flex items-center gap-3 px-4 py-3 cursor-grab active:cursor-grabbing"
          style={{ backgroundColor: `${block.color}12` }}
          {...attributes}
          {...listeners}
        >
          {/* Icon bubble */}
          <div
            className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center text-white shadow-sm"
            style={{ backgroundColor: block.color }}
          >
            <Icon className="w-4 h-4" />
          </div>

          <span className="font-semibold text-sm text-foreground flex-1">{block.label}</span>

          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            {/* 코드 블록일 때 노트 버튼 */}
            {isCodeBlock && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-muted-foreground hover:text-primary"
                onClick={openCodeModal}
                title="코드 편집"
              >
                <Code className="w-4 h-4" />
              </Button>
            )}
            {(block.fields?.length ?? 0) > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                onClick={() => setIsExpanded(!isExpanded)}
              >
                {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 text-muted-foreground hover:text-red-500"
              onClick={() => onDelete(block.instanceId)}
            >
              <Trash2 className="w-4 h-4" />
            </Button>
            <GripVertical className="w-4 h-4 text-muted-foreground/40" />
          </div>
        </div>

        {/* Fields */}
        {isExpanded && (block.fields?.length ?? 0) > 0 && (
          <div
            className="px-4 pb-4 pt-2 space-y-3 border-t"
            style={{ borderColor: `${block.color}20` }}
            onPointerDown={(e) => e.stopPropagation()}
          >
            {(block.fields || []).map((field) => (
              <div key={field.name} className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">
                  {field.label}
                </label>
                {field.type === "select" && field.options ? (
                  <Select
                    value={(block.fieldValues[field.name] as string) || (field.value as string) || field.options[0]?.value}
                    onValueChange={(v) => handleFieldChange(field.name, v)}
                  >
                    <SelectTrigger
                      className="h-8 text-xs rounded-xl border"
                      style={{ borderColor: `${block.color}44` }}
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {field.options.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Input
                    type={field.type === "number" ? "number" : "text"}
                    placeholder={field.placeholder}
                    value={block.fieldValues[field.name] || ""}
                    onChange={(e) => handleFieldChange(field.name, e.target.value)}
                    className="h-8 text-xs rounded-xl"
                    style={{ borderColor: `${block.color}44` }}
                  />
                )}
              </div>
            ))}
          </div>
        )}

        {/* Bottom output port dot */}
        {!isLast && (
          <div className="flex justify-center py-1" style={{ backgroundColor: `${block.color}08` }}>
            <div
              className="w-3 h-3 rounded-full border-2 border-background shadow-sm"
              style={{ backgroundColor: block.color }}
            />
          </div>
        )}
      </div>

      {/* Connector: animated arrow line to next block */}
      {!isLast && (
        <div className="flex flex-col items-center" style={{ height: 48 }}>
          <svg
            width="40"
            height="48"
            viewBox="0 0 40 48"
            fill="none"
            className="overflow-visible"
          >
            {/* dashed animated line */}
            <line
              x1="20" y1="0"
              x2="20" y2="34"
              stroke={block.color}
              strokeWidth="2"
              strokeDasharray="5 3"
              strokeLinecap="round"
            >
              <animate
                attributeName="stroke-dashoffset"
                from="16"
                to="0"
                dur="0.8s"
                repeatCount="indefinite"
              />
            </line>
            {/* arrowhead */}
            <polygon
              points="20,40 14,28 26,28"
              fill={block.color}
              opacity="0.9"
            />
          </svg>
        </div>
      )}

      {/* Python 코드 편집 모달 */}
      {isCodeBlock && (
        <Dialog open={isCodeModalOpen} onOpenChange={setIsCodeModalOpen}>
          <DialogContent className="sm:max-w-xl max-h-[80vh] flex flex-col rounded-2xl p-0 overflow-hidden">
            <DialogHeader className="px-4 py-3 border-b bg-muted/40 flex-shrink-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-white"
                    style={{ backgroundColor: block.color }}
                  >
                    <Code className="w-4 h-4" />
                  </div>
                  <DialogTitle className="text-sm font-semibold">Python 코드 편집</DialogTitle>
                </div>
              </div>
            </DialogHeader>
            <div className="flex-1 p-4 overflow-hidden flex flex-col">
              <Textarea
                value={tempCode}
                onChange={(e) => setTempCode(e.target.value)}
                placeholder="# Python 코드를 입력하세요&#10;print('Hello World')"
                className="flex-1 min-h-[300px] font-mono text-sm resize-none rounded-xl border-2 focus:border-primary/40"
                style={{ borderColor: `${block.color}40` }}
              />
              <p className="text-[10px] text-muted-foreground mt-2">
                변수 사용: {"{{variable_name}}"} 형식으로 입력
              </p>
            </div>
            <div className="px-4 py-3 border-t flex gap-2 justify-end flex-shrink-0">
              <Button
                variant="outline"
                size="sm"
                className="rounded-lg"
                onClick={() => setIsCodeModalOpen(false)}
              >
                취소
              </Button>
              <Button
                size="sm"
                className="rounded-lg"
                style={{ backgroundColor: block.color }}
                onClick={saveCodeAndClose}
              >
                저장
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}
