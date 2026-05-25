"use client"

import { useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Search,
  RefreshCw,
  Globe,
  Loader2,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  MousePointer,
  FormInput,
  List,
  Link2,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { api, type WorkflowValidationResponse, type PageAnalysisResponse } from "@/lib/api"
import type { WorkspaceBlock } from "@/types/blocks"

interface SelectorValidationPanelProps {
  blocks: WorkspaceBlock[]
}

interface ValidationResult {
  block_id: string
  block_type: string
  label: string
  selector: string
  is_valid: boolean
  match_count: number
  sample_text?: string
  confidence: number
  alternatives: string[]
  error?: string
}

export function SelectorValidationPanel({ blocks }: SelectorValidationPanelProps) {
  const [url, setUrl] = useState("")
  const [isValidating, setIsValidating] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [validationResult, setValidationResult] = useState<WorkflowValidationResponse | null>(null)
  const [pageAnalysis, setPageAnalysis] = useState<PageAnalysisResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expandedBlocks, setExpandedBlocks] = useState<Set<string>>(new Set())
  const [showPageAnalysis, setShowPageAnalysis] = useState(false)

  // 블록에서 URL 자동 추출
  const extractUrlFromBlocks = useCallback(() => {
    for (const block of blocks) {
      if (block.id === "open-site" || block.id === "navigate") {
        const blockUrl = block.fieldValues?.url
        if (blockUrl && typeof blockUrl === "string" && blockUrl.startsWith("http")) {
          setUrl(blockUrl)
          return
        }
      }
    }
  }, [blocks])

  // 셀렉터가 있는 블록만 필터링
  const blocksWithSelectors = blocks.filter((block) => {
    const selector = block.fieldValues?.selector
    return selector && typeof selector === "string" && selector.length > 0
  })

  // 워크플로우 검증
  const handleValidate = async () => {
    if (!url) {
      setError("URL을 입력하세요")
      return
    }

    if (blocksWithSelectors.length === 0) {
      setError("검증할 셀렉터가 있는 블록이 없습니다")
      return
    }

    setIsValidating(true)
    setError(null)
    setValidationResult(null)

    try {
      const result = await api.validateWorkflow(url, blocks)
      setValidationResult(result)

      if (!result.fetch_success) {
        setError(result.error || "페이지를 가져올 수 없습니다")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "검증 실패")
    } finally {
      setIsValidating(false)
    }
  }

  // 페이지 분석
  const handleAnalyzePage = async () => {
    if (!url) {
      setError("URL을 입력하세요")
      return
    }

    setIsAnalyzing(true)
    setError(null)
    setPageAnalysis(null)

    try {
      const result = await api.analyzePage(url)
      setPageAnalysis(result)
      setShowPageAnalysis(true)

      if (!result.success) {
        setError(result.error || "페이지 분석 실패")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "분석 실패")
    } finally {
      setIsAnalyzing(false)
    }
  }

  const toggleBlockExpand = (blockId: string) => {
    setExpandedBlocks((prev) => {
      const next = new Set(prev)
      if (next.has(blockId)) {
        next.delete(blockId)
      } else {
        next.add(blockId)
      }
      return next
    })
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return "text-green-500"
    if (confidence >= 0.5) return "text-yellow-500"
    return "text-red-500"
  }

  return (
    <div className="h-full flex flex-col p-4 gap-3 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Search className="w-4 h-4 text-muted-foreground" />
        <h3 className="text-sm font-semibold">셀렉터 검증</h3>
        <Badge variant="outline" className="ml-auto text-xs">
          {blocksWithSelectors.length}개 셀렉터
        </Badge>
      </div>

      {/* URL Input */}
      <div className="flex gap-2">
        <Input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com"
          className="flex-1 h-9 rounded-xl text-sm"
        />
        <Button
          size="sm"
          variant="ghost"
          onClick={extractUrlFromBlocks}
          className="h-9 px-2"
          title="블록에서 URL 추출"
        >
          <Globe className="w-4 h-4" />
        </Button>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2">
        <Button
          onClick={handleValidate}
          disabled={isValidating || !url || blocksWithSelectors.length === 0}
          className="flex-1 h-9 rounded-xl text-sm"
        >
          {isValidating ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <CheckCircle2 className="w-4 h-4 mr-2" />
          )}
          셀렉터 검증
        </Button>
        <Button
          onClick={handleAnalyzePage}
          disabled={isAnalyzing || !url}
          variant="outline"
          className="h-9 rounded-xl text-sm px-3"
          title="페이지 구조 분석"
        >
          {isAnalyzing ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 px-3 py-2 bg-red-500/10 rounded-xl text-sm text-red-500">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span className="truncate">{error}</span>
        </div>
      )}

      {/* Validation Results */}
      {validationResult && (
        <div className="flex-1 overflow-y-auto space-y-2">
          {/* Summary */}
          <div className="flex items-center gap-3 px-3 py-2 bg-muted/50 rounded-xl">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium text-green-600">
                {validationResult.summary.valid}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <XCircle className="w-4 h-4 text-red-500" />
              <span className="text-sm font-medium text-red-600">
                {validationResult.summary.invalid}
              </span>
            </div>
            {validationResult.js_required && (
              <Badge variant="secondary" className="ml-auto text-xs">
                JS 필요
              </Badge>
            )}
          </div>

          {/* Block Results */}
          {validationResult.blocks.map((block) => (
            <div
              key={block.block_id || block.selector}
              className={cn(
                "rounded-xl border overflow-hidden",
                block.is_valid ? "border-green-500/30 bg-green-500/5" : "border-red-500/30 bg-red-500/5"
              )}
            >
              {/* Block Header */}
              <button
                onClick={() => toggleBlockExpand(block.block_id || block.selector)}
                className="w-full flex items-center gap-2 px-3 py-2 hover:bg-muted/30 transition-colors"
              >
                {block.is_valid ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-500 shrink-0" />
                )}
                <span className="text-sm font-medium truncate flex-1 text-left">
                  {block.label || block.block_type}
                </span>
                <Badge variant="outline" className="text-xs shrink-0">
                  {block.match_count}개
                </Badge>
                {expandedBlocks.has(block.block_id || block.selector) ? (
                  <ChevronUp className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                )}
              </button>

              {/* Expanded Details */}
              {expandedBlocks.has(block.block_id || block.selector) && (
                <div className="px-3 pb-3 space-y-2 border-t border-border/50">
                  {/* Selector */}
                  <div className="mt-2">
                    <span className="text-xs text-muted-foreground">셀렉터:</span>
                    <code className="block mt-1 px-2 py-1 bg-muted/50 rounded text-xs font-mono break-all">
                      {block.selector}
                    </code>
                  </div>

                  {/* Confidence */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">신뢰도:</span>
                    <span className={cn("text-sm font-medium", getConfidenceColor(block.confidence))}>
                      {Math.round(block.confidence * 100)}%
                    </span>
                  </div>

                  {/* Sample Text */}
                  {block.sample_text && (
                    <div>
                      <span className="text-xs text-muted-foreground">샘플 텍스트:</span>
                      <p className="mt-1 text-xs text-foreground/80 line-clamp-2">
                        {block.sample_text}
                      </p>
                    </div>
                  )}

                  {/* Alternatives */}
                  {!block.is_valid && block.alternatives.length > 0 && (
                    <div>
                      <div className="flex items-center gap-1 text-xs text-yellow-600">
                        <Lightbulb className="w-3 h-3" />
                        <span>대안 셀렉터:</span>
                      </div>
                      <div className="mt-1 space-y-1">
                        {block.alternatives.slice(0, 3).map((alt, i) => (
                          <code
                            key={i}
                            className="block px-2 py-1 bg-yellow-500/10 rounded text-xs font-mono break-all cursor-pointer hover:bg-yellow-500/20"
                            onClick={() => {
                              navigator.clipboard.writeText(alt)
                            }}
                            title="클릭하여 복사"
                          >
                            {alt}
                          </code>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Error */}
                  {block.error && (
                    <div className="text-xs text-red-500">{block.error}</div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Page Analysis */}
      {showPageAnalysis && pageAnalysis?.success && (
        <div className="flex-1 overflow-y-auto space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold">페이지 분석 결과</h4>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowPageAnalysis(false)}
              className="h-6 px-2 text-xs"
            >
              닫기
            </Button>
          </div>

          {pageAnalysis.title && (
            <p className="text-xs text-muted-foreground truncate">
              {pageAnalysis.title}
            </p>
          )}

          {/* Forms */}
          {pageAnalysis.elements?.forms && pageAnalysis.elements.forms.length > 0 && (
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs font-medium">
                <FormInput className="w-3 h-3" />
                폼 ({pageAnalysis.elements.forms.length})
              </div>
              {pageAnalysis.elements.forms.map((form, i) => (
                <code
                  key={i}
                  className="block px-2 py-1 bg-muted/50 rounded text-xs font-mono truncate cursor-pointer hover:bg-muted"
                  onClick={() => navigator.clipboard.writeText(form.selector)}
                  title="클릭하여 복사"
                >
                  {form.selector}
                </code>
              ))}
            </div>
          )}

          {/* Inputs */}
          {pageAnalysis.elements?.inputs && pageAnalysis.elements.inputs.length > 0 && (
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs font-medium">
                <FormInput className="w-3 h-3" />
                입력창 ({pageAnalysis.elements.inputs.length})
              </div>
              {pageAnalysis.elements.inputs.slice(0, 5).map((input, i) => (
                <div
                  key={i}
                  className="px-2 py-1 bg-muted/50 rounded text-xs cursor-pointer hover:bg-muted"
                  onClick={() => navigator.clipboard.writeText(input.selector)}
                  title="클릭하여 복사"
                >
                  <code className="font-mono truncate block">{input.selector}</code>
                  {input.placeholder && (
                    <span className="text-muted-foreground">
                      placeholder: {input.placeholder}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Buttons */}
          {pageAnalysis.elements?.buttons && pageAnalysis.elements.buttons.length > 0 && (
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs font-medium">
                <MousePointer className="w-3 h-3" />
                버튼 ({pageAnalysis.elements.buttons.length})
              </div>
              {pageAnalysis.elements.buttons.slice(0, 5).map((btn, i) => (
                <div
                  key={i}
                  className="px-2 py-1 bg-muted/50 rounded text-xs cursor-pointer hover:bg-muted"
                  onClick={() => navigator.clipboard.writeText(btn.selector)}
                  title="클릭하여 복사"
                >
                  <code className="font-mono truncate block">{btn.selector}</code>
                  {btn.text && (
                    <span className="text-muted-foreground">
                      텍스트: {btn.text}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Lists */}
          {pageAnalysis.elements?.lists && pageAnalysis.elements.lists.length > 0 && (
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs font-medium">
                <List className="w-3 h-3" />
                목록 ({pageAnalysis.elements.lists.length})
              </div>
              {pageAnalysis.elements.lists.slice(0, 3).map((list, i) => (
                <div
                  key={i}
                  className="px-2 py-1 bg-muted/50 rounded text-xs cursor-pointer hover:bg-muted"
                  onClick={() => navigator.clipboard.writeText(list.item_selector)}
                  title="클릭하여 복사"
                >
                  <code className="font-mono truncate block">{list.item_selector}</code>
                  <span className="text-muted-foreground">
                    {list.item_count}개 항목
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Links */}
          {pageAnalysis.elements?.links && pageAnalysis.elements.links.length > 0 && (
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs font-medium">
                <Link2 className="w-3 h-3" />
                링크 ({pageAnalysis.elements.links.length})
              </div>
              {pageAnalysis.elements.links.slice(0, 5).map((link, i) => (
                <div
                  key={i}
                  className="px-2 py-1 bg-muted/50 rounded text-xs cursor-pointer hover:bg-muted"
                  onClick={() => navigator.clipboard.writeText(link.selector)}
                  title="클릭하여 복사"
                >
                  <code className="font-mono truncate block">{link.selector}</code>
                  {link.text && (
                    <span className="text-muted-foreground truncate block">
                      {link.text}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!validationResult && !showPageAnalysis && blocksWithSelectors.length === 0 && (
        <div className="flex-1 flex items-center justify-center text-center">
          <div className="text-muted-foreground text-sm">
            <Search className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p>셀렉터가 있는 블록이 없습니다</p>
            <p className="text-xs mt-1">클릭, 입력, 추출 블록을 추가하세요</p>
          </div>
        </div>
      )}

      {!validationResult && !showPageAnalysis && blocksWithSelectors.length > 0 && (
        <div className="flex-1 flex items-center justify-center text-center">
          <div className="text-muted-foreground text-sm">
            <CheckCircle2 className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p>URL을 입력하고 검증을 시작하세요</p>
            <p className="text-xs mt-1">
              실제 웹페이지에서 셀렉터가 유효한지 확인합니다
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
