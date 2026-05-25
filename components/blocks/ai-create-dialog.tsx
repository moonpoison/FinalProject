"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import {
  Upload,
  Loader2,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  FolderCode,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Info,
  RefreshCw
} from "lucide-react"
import { api, CodeVerificationResponse, CodeVerificationIssue } from "@/lib/api"

interface AIQuestion {
  id: string
  question: string
  type: "choice" | "text" | "confirm"
  options?: string[]
  default?: string
  hint?: string  // 질문에 대한 추가 설명
  required?: boolean
  placeholder?: string
}

interface ReferenceProject {
  name: string
  category: string
  similarity: number
  sites: string[]
  libraries: string[]
}

interface AICreateDialogProps {
  isOpen: boolean
  onClose: () => void
  onAnalyze: (prompt: string) => void
  onWorkflowGenerated?: (workflow: any) => void
  isAnalyzing: boolean
}

type Stage = "prompt" | "questions" | "generating" | "verifying"

export function AICreateDialog({
  isOpen,
  onClose,
  onAnalyze,
  onWorkflowGenerated,
  isAnalyzing,
}: AICreateDialogProps) {
  const [stage, setStage] = useState<Stage>("prompt")
  const [prompt, setPrompt] = useState("")
  const [questions, setQuestions] = useState<AIQuestion[]>([])
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [message, setMessage] = useState("")
  const [referenceProjects, setReferenceProjects] = useState<ReferenceProject[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  // 검증 관련 상태
  const [generatedWorkflow, setGeneratedWorkflow] = useState<any>(null)
  const [verification, setVerification] = useState<CodeVerificationResponse | null>(null)

  // 다이얼로그 닫힐 때 상태 초기화
  useEffect(() => {
    if (!isOpen) {
      setStage("prompt")
      setPrompt("")
      setQuestions([])
      setAnswers({})
      setMessage("")
      setReferenceProjects([])
      setError("")
      setIsLoading(false)
      setGeneratedWorkflow(null)
      setVerification(null)
    }
  }, [isOpen])

  // 프롬프트 분석 - 항상 질문 단계를 거침
  const handleAnalyze = async () => {
    if (!prompt.trim()) return

    setIsLoading(true)
    setError("")

    try {
      console.log("[AI Dialog] 프롬프트 분석 시작:", prompt)
      const response = await api.conversationAnalyze({
        prompt: prompt,
        answers: null
      })

      console.log("[AI Dialog] 분석 응답:", response)

      if (response.mode === "questions" && response.questions && response.questions.length > 0) {
        // 질문이 있으면 질문 단계로
        setQuestions(response.questions)
        setMessage(response.message || "")
        setReferenceProjects(response.reference_projects || [])

        // 기본값 설정
        const defaultAnswers: Record<string, string> = {}
        response.questions.forEach((q: AIQuestion) => {
          if (q.default) {
            defaultAnswers[q.id] = q.default
          }
        })
        setAnswers(defaultAnswers)
        setStage("questions")
        setIsLoading(false)
      } else if (response.mode === "workflow" && response.workflow) {
        // 워크플로우가 바로 생성된 경우에도 확인 단계 추가
        console.log("[AI Dialog] 워크플로우 바로 생성됨 - 확인 질문 추가")

        // 기본 확인 질문 생성
        const confirmQuestions: AIQuestion[] = [
          {
            id: "confirm_workflow",
            question: "분석 결과를 확인하셨나요? 워크플로우를 생성하시겠습니까?",
            type: "confirm",
            options: ["예, 생성합니다", "아니오, 수정이 필요합니다"],
            default: "예, 생성합니다"
          },
          {
            id: "additional_request",
            question: "추가로 필요한 설정이 있으면 입력해주세요",
            type: "text",
            placeholder: "예: 반복 횟수 10회, 대기시간 3초 등",
            default: ""
          }
        ]

        setQuestions(confirmQuestions)
        setMessage(response.message || `'${prompt}' 작업을 분석했습니다. 워크플로우 생성 준비가 완료되었습니다.`)
        setReferenceProjects(response.reference_projects || [])
        setAnswers({ "confirm_workflow": "예, 생성합니다" })
        setStage("questions")
        setIsLoading(false)
      } else {
        // 폴백: 기존 스트리밍 방식 사용
        console.log("[AI Dialog] 폴백: 스트리밍 모드")
        setIsLoading(false)
        onAnalyze(prompt)
      }
    } catch (err: any) {
      console.error("[AI Dialog] 대화형 AI 오류:", err)
      // 오류 시 기존 방식으로 폴백
      setIsLoading(false)
      onAnalyze(prompt)
    }
  }

  // 답변 제출 → 워크플로우 생성 → 자동 검증 및 개선
  const handleSubmitAnswers = async () => {
    setIsLoading(true)
    setStage("generating")
    setError("")
    setVerification(null)

    try {
      console.log("[AI Dialog] 워크플로우 생성 요청:", { prompt, answers, questions })
      const response = await api.conversationAnalyze({
        prompt: prompt,
        answers: answers,
        questions: questions  // 질문 내용도 함께 전송
      })

      console.log("[AI Dialog] 응답 수신:", response)

      if (response.mode === "workflow" && response.workflow) {
        const groups = response.workflow.groups || []
        const totalSteps = groups.reduce((sum: number, g: any) => sum + (g.steps?.length || 0), 0)

        console.log(`[AI Dialog] 워크플로우: ${groups.length}개 그룹, ${totalSteps}개 스텝`)

        if (totalSteps === 0) {
          response.workflow = {
            task_name: prompt.slice(0, 30),
            summary: `'${prompt.slice(0, 50)}' 자동화`,
            confidence: 50,
            groups: [
              {
                id: "g1",
                label: "시작",
                description: "워크플로우 시작",
                color: "#22c55e",
                steps: [
                  { id: "s1", label: "시작", description: "시작 블록", block_type: "start", color: "#22c55e", field_values: {} }
                ]
              }
            ]
          }
        }

        setGeneratedWorkflow(response.workflow)

        // 검증 단계 건너뛰고 바로 완료 - 워크플로우 생성
        console.log("[AI Dialog] 워크플로우 생성 완료, 바로 적용")
        if (onWorkflowGenerated) {
          onWorkflowGenerated(response.workflow)
        }
        onClose()
      } else {
        setError("워크플로우 생성에 실패했습니다.")
        setStage("questions")
      }
    } catch (err: any) {
      console.error("[AI Dialog] 워크플로우 생성 오류:", err)
      setError(err.message || "워크플로우 생성 중 오류가 발생했습니다.")
      setStage("questions")
    } finally {
      setIsLoading(false)
    }
  }

  // 검증 완료 후 블록 생성
  const handleApproveAndCreate = () => {
    if (generatedWorkflow && onWorkflowGenerated) {
      onWorkflowGenerated(generatedWorkflow)
    }
    onClose()
  }

  // 재생성 요청
  const handleRegenerate = async () => {
    setVerification(null)
    setGeneratedWorkflow(null)
    setStage("generating")
    setIsLoading(true)

    try {
      const response = await api.conversationAnalyze({
        prompt: prompt,
        answers: answers,
        questions: questions  // 질문 내용도 함께 전송
      })

      if (response.mode === "workflow" && response.workflow) {
        setGeneratedWorkflow(response.workflow)
        setStage("verifying")

        const verificationResult = await api.verifyCode(response.workflow, prompt)
        setVerification(verificationResult)

        if (verificationResult.improved_workflow) {
          setGeneratedWorkflow(verificationResult.improved_workflow)
        }
      }
    } catch (err: any) {
      setError(err.message || "재생성 중 오류가 발생했습니다.")
      setStage("questions")
    } finally {
      setIsLoading(false)
    }
  }

  // 이슈 아이콘 렌더링
  const getIssueIcon = (severity: string) => {
    switch (severity) {
      case "error":
        return <AlertCircle className="w-4 h-4 text-red-500" />
      case "warning":
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />
      default:
        return <Info className="w-4 h-4 text-blue-500" />
    }
  }

  // 점수에 따른 색상
  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-green-500"
    if (score >= 70) return "text-yellow-500"
    if (score >= 50) return "text-orange-500"
    return "text-red-500"
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      if (stage === "prompt") handleAnalyze()
      else if (stage === "questions") handleSubmitAnswers()
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent
        className="rounded-2xl p-0 overflow-hidden max-h-[60vh] flex flex-col"
        style={{ width: '700px', maxWidth: '700px' }}
      >
        {/* Header */}
        <div className="px-4 pt-4 pb-2 shrink-0 bg-muted/40">
          <DialogHeader>
            <DialogTitle className="text-base">AI 자동화 생성</DialogTitle>
            <DialogDescription className="text-left text-xs">
              {stage === "prompt" && "작업을 설명해주세요"}
              {stage === "questions" && "확인이 필요합니다"}
              {stage === "generating" && "생성 중..."}
              {stage === "verifying" && "코드 검증 결과"}
            </DialogDescription>
          </DialogHeader>
        </div>

        {/* Content */}
        <div className="px-4 py-2 space-y-2 overflow-y-auto flex-1">
          {error && (
            <div className="p-2 rounded-lg bg-destructive/10 text-destructive text-xs">
              {error}
            </div>
          )}

          {/* Stage 1: Prompt Input */}
          {stage === "prompt" && (
            <>
              <div className="flex flex-wrap gap-1">
                {[
                  "카페 글쓰기",
                  "가격 수집",
                  "자동 팔로우",
                ].map((example) => (
                  <button
                    key={example}
                    onClick={() => setPrompt(example)}
                    className="text-[10px] px-2 py-0.5 rounded-full border border-primary/25 bg-primary/5 text-primary hover:bg-primary/10 transition-colors"
                  >
                    {example}
                  </button>
                ))}
              </div>

              <div className="relative">
                <Textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="예: 네이버 카페에 글 자동 등록"
                  className="min-h-[70px] rounded-lg resize-none pr-8 border border-primary/20 focus:border-primary/40 text-xs"
                />
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-1 bottom-1 rounded-md hover:bg-primary/10 h-6 w-6"
                  title="파일 첨부"
                >
                  <Upload className="w-3 h-3 text-muted-foreground" />
                </Button>
              </div>

              <p className="text-[10px] text-muted-foreground">
                Ctrl+Enter로 분석
              </p>
            </>
          )}

          {/* Stage 2: Questions */}
          {stage === "questions" && (
            <>
              {/* Questions */}
              <div className="space-y-3">
                {questions.map((q, index) => (
                  <div key={q.id} className="space-y-2 p-3 rounded-xl bg-muted/30 border border-muted">
                    <div className="flex items-start gap-2">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs font-bold flex items-center justify-center mt-0.5">
                        {index + 1}
                      </span>
                      <Label className="text-sm font-medium leading-snug flex-1">{q.question}</Label>
                    </div>

                    {q.type === "choice" && q.options && (
                      <RadioGroup
                        value={answers[q.id] || q.default || ""}
                        onValueChange={(value) => setAnswers({ ...answers, [q.id]: value })}
                        className="flex flex-wrap gap-2 ml-8"
                      >
                        {q.options.map((option) => (
                          <div key={option} className="flex items-center">
                            <RadioGroupItem value={option} id={`${q.id}-${option}`} className="sr-only" />
                            <Label
                              htmlFor={`${q.id}-${option}`}
                              className={`px-3 py-1.5 rounded-lg border cursor-pointer text-sm transition-colors ${
                                answers[q.id] === option
                                  ? "bg-primary text-white border-primary"
                                  : "bg-background border-muted-foreground/20 hover:bg-muted"
                              }`}
                            >
                              {option}
                            </Label>
                          </div>
                        ))}
                      </RadioGroup>
                    )}

                    {q.type === "confirm" && (
                      <RadioGroup
                        value={answers[q.id] || q.default || ""}
                        onValueChange={(value) => setAnswers({ ...answers, [q.id]: value })}
                        className="flex gap-2 ml-8"
                      >
                        {(q.options || ["예", "아니오"]).map((option) => (
                          <div key={option} className="flex items-center">
                            <RadioGroupItem value={option} id={`${q.id}-${option}`} className="sr-only" />
                            <Label
                              htmlFor={`${q.id}-${option}`}
                              className={`px-3 py-1.5 rounded-lg border cursor-pointer text-sm transition-colors ${
                                answers[q.id] === option
                                  ? "bg-primary text-white border-primary"
                                  : "bg-background border-muted-foreground/20 hover:bg-muted"
                              }`}
                            >
                              {option}
                            </Label>
                          </div>
                        ))}
                      </RadioGroup>
                    )}

                    {q.type === "text" && (
                      <Input
                        value={answers[q.id] || ""}
                        onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
                        placeholder={q.placeholder || q.default || "입력"}
                        className="rounded-lg h-9 text-sm ml-8 w-[calc(100%-2rem)]"
                      />
                    )}
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Stage 3: Generating */}
          {stage === "generating" && (
            <div className="flex flex-col items-center justify-center py-4 gap-2">
              <Loader2 className="w-6 h-6 text-primary animate-spin" />
              <p className="text-xs text-muted-foreground">생성 중...</p>
            </div>
          )}

          {/* Stage 4: Verification Results */}
          {stage === "verifying" && verification && (
            <div className="space-y-3">
              {/* 점수 및 요약 - 점수에 따라 다른 UI */}
              <div className={`p-4 rounded-xl border ${
                verification.score >= 85
                  ? "bg-green-50 border-green-200 dark:bg-green-950/20 dark:border-green-800"
                  : verification.score >= 70
                  ? "bg-blue-50 border-blue-200 dark:bg-blue-950/20 dark:border-blue-800"
                  : "bg-yellow-50 border-yellow-200 dark:bg-yellow-950/20 dark:border-yellow-800"
              }`}>
                <div className="flex items-center gap-3">
                  {verification.score >= 85 ? (
                    <CheckCircle2 className="w-8 h-8 text-green-500" />
                  ) : verification.score >= 70 ? (
                    <CheckCircle2 className="w-8 h-8 text-blue-500" />
                  ) : (
                    <AlertTriangle className="w-8 h-8 text-yellow-500" />
                  )}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-lg font-bold">
                        {verification.score >= 85 ? "준비 완료!" : verification.score >= 70 ? "검증 완료" : "검토 필요"}
                      </span>
                      <span className={`text-sm font-medium px-2 py-0.5 rounded-full ${
                        verification.score >= 85
                          ? "bg-green-200 text-green-800 dark:bg-green-800 dark:text-green-200"
                          : verification.score >= 70
                          ? "bg-blue-200 text-blue-800 dark:bg-blue-800 dark:text-blue-200"
                          : "bg-yellow-200 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-200"
                      }`}>
                        {verification.score}점
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {verification.summary}
                    </p>
                  </div>
                </div>
              </div>

              {/* 워크플로우 요약 */}
              {generatedWorkflow && (
                <div className="p-3 rounded-xl bg-muted/30 border border-muted">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-primary" />
                    <span className="text-sm font-medium">{generatedWorkflow.task_name}</span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {generatedWorkflow.groups?.map((g: any, idx: number) => (
                      <span
                        key={idx}
                        className="text-xs px-2 py-1 rounded-full"
                        style={{ backgroundColor: g.color + "20", color: g.color }}
                      >
                        {g.label} ({g.steps?.length || 0})
                      </span>
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    총 {generatedWorkflow.groups?.reduce((sum: number, g: any) => sum + (g.steps?.length || 0), 0) || 0}개 블록이 생성됩니다
                  </p>
                </div>
              )}

              {/* 자동 개선 내역 (있을 경우에만) */}
              {verification.issues.length > 0 && (
                <div className="space-y-1">
                  <h4 className="text-xs font-medium text-muted-foreground">자동 개선 내역</h4>
                  <div className="max-h-24 overflow-y-auto space-y-1">
                    {verification.issues.map((issue, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-xs text-muted-foreground">
                        <CheckCircle2 className="w-3 h-3 text-green-500 shrink-0" />
                        <span>{issue.message}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Verifying Loading */}
          {stage === "verifying" && !verification && (
            <div className="flex flex-col items-center justify-center py-6 gap-3">
              <div className="relative">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
                <Sparkles className="w-4 h-4 text-primary absolute -top-1 -right-1 animate-pulse" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium">AI가 코드를 검증하고 있습니다</p>
                <p className="text-xs text-muted-foreground mt-1">최적의 워크플로우를 자동으로 생성 중...</p>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="px-4 pb-4 pt-1 shrink-0">
          <div className="flex gap-2">
            {stage === "prompt" && (
              <>
                <Button
                  variant="outline"
                  onClick={onClose}
                  className="flex-1 rounded-lg h-8 text-xs"
                >
                  취소
                </Button>
                <Button
                  onClick={handleAnalyze}
                  disabled={!prompt.trim() || isLoading || isAnalyzing}
                  className="flex-1 rounded-lg h-8 bg-primary hover:bg-primary/90 font-medium text-xs"
                >
                  {(isLoading || isAnalyzing) ? (
                    <>
                      <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                      분석 중
                    </>
                  ) : (
                    <>
                      분석
                      <ArrowRight className="w-3 h-3 ml-1" />
                    </>
                  )}
                </Button>
              </>
            )}

            {stage === "questions" && (
              <>
                <Button
                  variant="outline"
                  onClick={() => setStage("prompt")}
                  className="rounded-lg h-8 text-xs px-3"
                >
                  <ArrowLeft className="w-3 h-3 mr-1" />
                  이전
                </Button>
                <Button
                  onClick={handleSubmitAnswers}
                  disabled={isLoading}
                  className="flex-1 rounded-lg h-8 bg-primary hover:bg-primary/90 font-medium text-xs"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                      생성 중
                    </>
                  ) : (
                    <>
                      생성
                      <Sparkles className="w-3 h-3 ml-1" />
                    </>
                  )}
                </Button>
              </>
            )}

            {stage === "verifying" && verification && (
              <>
                {verification.score < 85 && (
                  <Button
                    variant="outline"
                    onClick={handleRegenerate}
                    disabled={isLoading}
                    className="rounded-lg h-8 text-xs px-3"
                  >
                    <RefreshCw className={`w-3 h-3 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
                    재생성
                  </Button>
                )}
                <Button
                  onClick={handleApproveAndCreate}
                  disabled={isLoading}
                  className={`flex-1 rounded-lg h-9 font-medium text-sm ${
                    verification.score >= 85
                      ? "bg-green-600 hover:bg-green-700"
                      : verification.score >= 70
                      ? "bg-blue-600 hover:bg-blue-700"
                      : "bg-yellow-600 hover:bg-yellow-700"
                  }`}
                >
                  {verification.score >= 85 ? (
                    <>
                      <Sparkles className="w-4 h-4 mr-1" />
                      블록 생성하기
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4 mr-1" />
                      확인 및 생성
                    </>
                  )}
                </Button>
              </>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
