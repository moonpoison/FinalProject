"use client"

import { useDraggable } from "@dnd-kit/core"
import { CSS } from "@dnd-kit/utilities"
import {
  Play, Globe, ArrowRight, ArrowLeft, ArrowRightCircle,
  MousePointer, MousePointer2, MousePointerClick,
  Keyboard, Command, Zap, Eraser,
  Download, FileSpreadsheet, FileText, FileInput,
  Clock, Repeat, GitBranch, GripVertical,
  CalendarClock, RefreshCw, MoveVertical, Loader,
  ScanSearch, Camera, PanelTopOpen, XCircle, LayoutGrid, Frame,
  Scan, Hand, List, CheckSquare, Upload,
  TextCursor, Rows3, CodeXml,
  Variable, Mail, MessageSquare, ListOrdered,
  Octagon, SquareX, Terminal, ShieldAlert,
  Globe2, ListTree, Braces, Cookie, KeyRound,
} from "lucide-react"

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
}

interface DraggableBlockProps {
  block: BlockDefinition
  isPalette?: boolean
}

export function DraggableBlock({ block, isPalette = true }: DraggableBlockProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: isPalette ? `palette-${block.id}` : block.id,
    data: { block, isPalette },
  })

  const style = transform
    ? {
        transform: CSS.Translate.toString(transform),
        zIndex: isDragging ? 1000 : undefined,
      }
    : undefined

  const Icon = iconMap[block.icon] || Play

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={`
        flex items-center gap-3 px-4 py-3 rounded-2xl cursor-grab active:cursor-grabbing
        font-semibold text-white shadow-lg transition-all duration-200
        hover:scale-105 hover:shadow-xl select-none
        ${isDragging ? "opacity-70 scale-105 shadow-2xl" : ""}
      `}
      role="button"
      tabIndex={0}
    >
      <div
        className="flex items-center justify-center w-8 h-8 rounded-xl"
        style={{ backgroundColor: "rgba(255,255,255,0.2)" }}
      >
        <Icon className="w-5 h-5" />
      </div>
      <span className="text-sm">{block.label}</span>
      <GripVertical className="w-4 h-4 ml-auto opacity-50" />
    </div>
  )
}
