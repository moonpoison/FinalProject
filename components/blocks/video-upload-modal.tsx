"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import {
  X,
  Upload,
  Video,
  Loader2,
  CheckCircle,
  AlertCircle,
  Play,
  FileText,
  Layers,
  Sparkles,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { api, type VideoDetailResponse } from "@/lib/api"

// 워크플로우 타입 정의
interface WorkflowStep {
  id: string
  label: string
  description: string
  blockType: string
  color: string
  fieldValues?: Record<string, any>
}

interface WorkflowGroup {
  id: string
  label: string
  description: string
  color: string
  steps: WorkflowStep[]
}

interface WorkflowData {
  taskName: string
  summary: string
  confidence: number
  groups: WorkflowGroup[]
}

interface VideoUploadModalProps {
  isOpen: boolean
  onClose: () => void
  onComplete: (blocks: any[]) => void
  onWorkflowReady?: (workflow: WorkflowData) => void  // 워크플로우 프리뷰용
}

type UploadStatus =
  | "idle"
  | "uploading"
  | "processing"
  | "extracting_audio"
  | "extracting_frames"
  | "transcribing"
  | "transcript_review"
  | "analyzing"
  | "generating"
  | "workflow_generating"
  | "completed"
  | "failed"

const STATUS_LABELS: Record<UploadStatus, string> = {
  idle: "영상을 업로드하세요",
  uploading: "영상 업로드 중...",
  processing: "영상 처리 시작...",
  extracting_audio: "오디오 추출 중...",
  extracting_frames: "프레임 추출 중...",
  transcribing: "음성 인식 중...",
  transcript_review: "음성 인식 결과 확인",
  analyzing: "AI 분석 중...",
  generating: "블록 생성 중...",
  workflow_generating: "워크플로우 생성 중...",
  completed: "분석 완료!",
  failed: "오류 발생",
}

export function VideoUploadModal({ isOpen, onClose, onComplete, onWorkflowReady }: VideoUploadModalProps) {
  const [status, setStatus] = useState<UploadStatus>("idle")
  const [progress, setProgress] = useState(0)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [videoId, setVideoId] = useState<string | null>(null)
  const [videoDetail, setVideoDetail] = useState<VideoDetailResponse | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [editedTranscript, setEditedTranscript] = useState<string>("")
  const [isTranscriptConfirmed, setIsTranscriptConfirmed] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollingRef = useRef<NodeJS.Timeout | null>(null)
  const workflowGeneratedRef = useRef<boolean>(false)
  const transcriptShownRef = useRef<boolean>(false)

  const resetState = useCallback(() => {
    setStatus("idle")
    setProgress(0)
    setErrorMessage(null)
    setVideoId(null)
    setVideoDetail(null)
    setSelectedFile(null)
    setEditedTranscript("")
    setIsTranscriptConfirmed(false)
    workflowGeneratedRef.current = false
    transcriptShownRef.current = false
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!isOpen) {
      resetState()
    }
  }, [isOpen, resetState])

  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [])

  // 영상 분석 결과로 AI 워크플로우 생성
  const generateWorkflowFromVideo = useCallback(async (detail: VideoDetailResponse, confirmedTranscript?: string) => {
    if (!detail.analysis_result || workflowGeneratedRef.current) return

    workflowGeneratedRef.current = true
    setStatus("workflow_generating")
    setProgress(95)

    try {
      // 사용자가 수정한 음성 텍스트가 있으면 그것을 우선 사용
      const transcriptToUse = confirmedTranscript || detail.transcript || ""

      // 음성 텍스트가 있으면 그것을 프롬프트로 사용 (분석 결과보다 우선)
      const generatedPrompt = transcriptToUse ||
        detail.analysis_result.generated_prompt ||
        detail.analysis_result.task_summary ||
        "화면 녹화 작업 자동화"

      // detected_actions가 있으면 프롬프트에 추가
      let enhancedPrompt = generatedPrompt
      if (detail.analysis_result.detected_actions?.length > 0) {
        const actions = detail.analysis_result.detected_actions
        const actionStrings = actions.map((a: any, i: number) => {
          if (typeof a === 'string') return `${i + 1}. ${a}`
          return `${i + 1}. ${a.action || a.element || ''}`
        })
        enhancedPrompt += "\n\n감지된 작업 단계:\n" + actionStrings.join("\n")
      }
      if (detail.analysis_result.detected_site) {
        enhancedPrompt += `\n\n대상 사이트: ${detail.analysis_result.detected_site}`
      }
      if (detail.analysis_result.detected_url) {
        enhancedPrompt += `\nURL: ${detail.analysis_result.detected_url}`
      }

      console.log("[Video] AI 워크플로우 생성 요청:", enhancedPrompt)

      const response = await api.conversationAnalyze({
        prompt: enhancedPrompt,
        answers: null
      })

      if (response.mode === "workflow" && response.workflow) {
        // 워크플로우 데이터를 AIPreviewModal 형식으로 변환
        const workflowData: WorkflowData = {
          taskName: response.workflow.task_name || detail.analysis_result.task_name || "영상 분석 자동화",
          summary: response.workflow.summary || detail.analysis_result.task_summary || "영상에서 분석된 작업입니다.",
          confidence: response.workflow.confidence || detail.analysis_result.confidence * 100 || 75,
          groups: (response.workflow.groups || []).map((g: any) => ({
            id: g.id,
            label: g.label,
            description: g.description,
            color: g.color,
            steps: (g.steps || []).map((s: any) => ({
              id: s.id,
              label: s.label,
              description: s.description,
              blockType: s.block_type,
              color: s.color,
              fieldValues: s.field_values || {}
            }))
          }))
        }

        console.log("[Video] 워크플로우 생성 완료:", workflowData)
        setStatus("completed")
        setProgress(100)

        // 워크플로우 프리뷰 콜백 호출
        if (onWorkflowReady) {
          onClose()
          onWorkflowReady(workflowData)
        }
      } else if (response.mode === "questions") {
        // 질문이 필요한 경우 - 기본값으로 워크플로우 생성 시도
        console.log("[Video] AI가 질문을 요청함, 기본값으로 재시도")
        const defaultAnswers: Record<string, string> = {}
        response.questions?.forEach((q: any) => {
          if (q.default) defaultAnswers[q.id] = q.default
          else if (q.options?.length > 0) defaultAnswers[q.id] = q.options[0]
        })

        const retryResponse = await api.conversationAnalyze({
          prompt: enhancedPrompt,
          answers: defaultAnswers
        })

        if (retryResponse.mode === "workflow" && retryResponse.workflow) {
          const workflowData: WorkflowData = {
            taskName: retryResponse.workflow.task_name || "영상 분석 자동화",
            summary: retryResponse.workflow.summary || "영상에서 분석된 작업입니다.",
            confidence: retryResponse.workflow.confidence || 75,
            groups: (retryResponse.workflow.groups || []).map((g: any) => ({
              id: g.id,
              label: g.label,
              description: g.description,
              color: g.color,
              steps: (g.steps || []).map((s: any) => ({
                id: s.id,
                label: s.label,
                description: s.description,
                blockType: s.block_type,
                color: s.color,
                fieldValues: s.field_values || {}
              }))
            }))
          }

          setStatus("completed")
          setProgress(100)

          if (onWorkflowReady) {
            onClose()
            onWorkflowReady(workflowData)
          }
        } else {
          // 폴백: 기존 방식으로 블록 생성
          setStatus("completed")
          setProgress(100)
        }
      }
    } catch (error) {
      console.error("[Video] 워크플로우 생성 오류:", error)
      // 오류 시 기존 completed 상태로 폴백
      setStatus("completed")
      setProgress(100)
    }
  }, [onClose, onWorkflowReady])

  const pollVideoStatus = useCallback(async (id: string) => {
    try {
      const detail = await api.getVideo(id)
      setProgress(detail.progress)
      setVideoDetail(detail)

      // 음성 인식 완료 후 확인 단계로 전환 (아직 확인 안 했고, transcript가 있을 때)
      if (detail.transcript && !transcriptShownRef.current && !isTranscriptConfirmed) {
        transcriptShownRef.current = true
        setEditedTranscript(detail.transcript)
        setStatus("transcript_review")
        // 폴링 일시 중지 (확인 후 재개)
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }
        return
      }

      if (detail.status === "completed") {
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }

        // 이미 transcript 확인을 했으면 워크플로우 생성 진행
        if (isTranscriptConfirmed && onWorkflowReady && detail.analysis_result) {
          generateWorkflowFromVideo(detail, editedTranscript)
        } else if (!onWorkflowReady) {
          setStatus("completed")
        }
        // transcript 확인 안 했으면 대기 (위에서 처리됨)
      } else if (detail.status === "failed") {
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }
        setStatus("failed")
        setErrorMessage(detail.error_message || "영상 처리 중 오류가 발생했습니다.")
      } else if (isTranscriptConfirmed) {
        // 확인 완료 후에는 일반 상태 업데이트
        setStatus(detail.status as UploadStatus)
      }
    } catch {
      // Ignore polling errors
    }
  }, [generateWorkflowFromVideo, onWorkflowReady, isTranscriptConfirmed, editedTranscript])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      setErrorMessage(null)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    try {
      setStatus("uploading")
      setProgress(0)

      const response = await api.uploadVideo(selectedFile)
      setVideoId(response.id)
      setStatus(response.status as UploadStatus)

      // Start polling for status
      pollingRef.current = setInterval(() => {
        pollVideoStatus(response.id)
      }, 2000)
    } catch (error) {
      setStatus("failed")
      setErrorMessage(error instanceof Error ? error.message : "업로드 실패")
    }
  }

  const handleApplyBlocks = async () => {
    if (!videoId || !videoDetail?.generated_blocks) return

    onComplete(videoDetail.generated_blocks)
    onClose()
  }

  // 음성 인식 결과 확인 후 계속 진행
  const handleConfirmTranscript = useCallback(async () => {
    setIsTranscriptConfirmed(true)
    setStatus("analyzing")
    setProgress(70)

    // 백엔드 처리가 완료될 때까지 다시 폴링 시작
    if (videoId) {
      pollingRef.current = setInterval(() => {
        pollVideoStatus(videoId)
      }, 2000)

      // 즉시 한번 체크
      const detail = await api.getVideo(videoId)
      if (detail.status === "completed" && detail.analysis_result && onWorkflowReady) {
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }
        generateWorkflowFromVideo(detail, editedTranscript)
      }
    }
  }, [videoId, pollVideoStatus, editedTranscript, generateWorkflowFromVideo, onWorkflowReady])

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (file && file.type.startsWith("video/")) {
      setSelectedFile(file)
      setErrorMessage(null)
    }
  }

  if (!isOpen) return null

  const isProcessing = ["uploading", "processing", "extracting_audio", "extracting_frames", "transcribing", "analyzing", "generating", "workflow_generating"].includes(status)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-background rounded-3xl shadow-2xl w-full max-w-lg mx-4 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <Video className="w-4 h-4 text-primary" />
            </div>
            <div>
              <h2 className="font-bold text-sm">영상으로 자동화 만들기</h2>
              <p className="text-xs text-muted-foreground">화면 녹화를 업로드하면 AI가 분석합니다</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-xl hover:bg-secondary flex items-center justify-center"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {status === "idle" && (
            <>
              {/* Drop zone */}
              <div
                className={`border-2 border-dashed rounded-2xl p-8 text-center transition-colors ${
                  selectedFile ? "border-primary bg-primary/5" : "border-border hover:border-muted-foreground"
                }`}
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/*"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                {selectedFile ? (
                  <div className="space-y-2">
                    <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto">
                      <Video className="w-6 h-6 text-primary" />
                    </div>
                    <p className="font-medium text-sm">{selectedFile.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="rounded-xl"
                      onClick={(e) => {
                        e.stopPropagation()
                        setSelectedFile(null)
                      }}
                    >
                      다른 파일 선택
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="w-14 h-14 rounded-2xl bg-muted flex items-center justify-center mx-auto">
                      <Upload className="w-6 h-6 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="font-medium text-sm">영상 파일을 드래그하거나 클릭하세요</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        MP4, WebM, MOV 지원 (최대 100MB)
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="bg-secondary/50 rounded-xl p-4 space-y-2">
                <h4 className="text-xs font-semibold flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-primary" />
                  AI가 분석하는 내용
                </h4>
                <ul className="text-xs text-muted-foreground space-y-1">
                  <li>• 화면에서 수행하는 작업 단계 인식</li>
                  <li>• 음성 설명 텍스트 변환 및 이해</li>
                  <li>• 자동화 가능한 워크플로우 추출</li>
                  <li>• 블록으로 자동 변환</li>
                </ul>
              </div>

              {errorMessage && (
                <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                  <p className="text-xs text-red-700">{errorMessage}</p>
                </div>
              )}
            </>
          )}

          {isProcessing && (
            <div className="space-y-4 py-4">
              <div className="flex flex-col items-center gap-4">
                <div className="relative w-20 h-20">
                  {/* Progress Circle */}
                  <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
                    {/* Background circle */}
                    <circle
                      cx="40"
                      cy="40"
                      r="36"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="4"
                      className="text-primary/20"
                    />
                    {/* Progress circle */}
                    <circle
                      cx="40"
                      cy="40"
                      r="36"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="4"
                      strokeLinecap="round"
                      className="text-primary transition-all duration-300"
                      style={{
                        strokeDasharray: `${2 * Math.PI * 36}`,
                        strokeDashoffset: `${2 * Math.PI * 36 * (1 - progress / 100)}`,
                      }}
                    />
                  </svg>
                  {/* Center percentage */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-lg font-bold text-primary">{progress}%</span>
                  </div>
                </div>
                <div className="text-center">
                  <p className="font-medium text-sm">{STATUS_LABELS[status]}</p>
                </div>
              </div>

              {/* Progress steps */}
              <div className="space-y-2 pt-4">
                {[
                  { id: "extracting_audio", label: "오디오 추출", icon: FileText },
                  { id: "extracting_frames", label: "프레임 추출", icon: Layers },
                  { id: "transcribing", label: "음성 인식", icon: FileText },
                  { id: "analyzing", label: "AI 분석", icon: Sparkles },
                  { id: "generating", label: "블록 생성", icon: Play },
                  { id: "workflow_generating", label: "워크플로우 생성", icon: Sparkles },
                ].map((step, i) => {
                  const stepOrder = ["extracting_audio", "extracting_frames", "transcribing", "analyzing", "generating", "workflow_generating"]
                  const currentIndex = stepOrder.indexOf(status)
                  const stepIndex = stepOrder.indexOf(step.id)
                  const isCompleted = stepIndex < currentIndex
                  const isCurrent = step.id === status

                  return (
                    <div
                      key={step.id}
                      className={`flex items-center gap-3 px-4 py-2 rounded-xl transition-colors ${
                        isCurrent ? "bg-primary/10" : isCompleted ? "bg-green-50" : "bg-muted/30"
                      }`}
                    >
                      <div className={`w-6 h-6 rounded-lg flex items-center justify-center ${
                        isCurrent ? "bg-primary text-primary-foreground" : isCompleted ? "bg-green-500 text-white" : "bg-muted text-muted-foreground"
                      }`}>
                        {isCompleted ? (
                          <CheckCircle className="w-3.5 h-3.5" />
                        ) : isCurrent ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <step.icon className="w-3.5 h-3.5" />
                        )}
                      </div>
                      <span className={`text-xs font-medium ${isCurrent ? "text-foreground" : isCompleted ? "text-green-700" : "text-muted-foreground"}`}>
                        {step.label}
                      </span>
                    </div>
                  )
                })}
              </div>

            </div>
          )}

          {/* 음성 인식 결과 확인/수정 단계 */}
          {status === "transcript_review" && (
            <div className="space-y-4 py-2">
              <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-2xl">
                <div className="w-10 h-10 rounded-xl bg-blue-500 flex items-center justify-center flex-shrink-0">
                  <FileText className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="font-semibold text-sm text-blue-800">음성 인식 완료!</p>
                  <p className="text-xs text-blue-700">
                    아래 내용을 확인하고 필요시 수정하세요
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-primary" />
                  음성 인식 결과 (수정 가능)
                </label>
                <textarea
                  value={editedTranscript}
                  onChange={(e) => setEditedTranscript(e.target.value)}
                  className="w-full h-40 p-3 text-sm border rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="음성 인식 결과가 여기에 표시됩니다..."
                />
                <p className="text-[10px] text-muted-foreground">
                  총 {editedTranscript.length}자 • 이 내용을 기반으로 워크플로우가 생성됩니다
                </p>
              </div>

              <div className="bg-amber-50 rounded-xl p-3 border border-amber-100">
                <p className="text-xs text-amber-800">
                  <strong>💡 팁:</strong> 자동화하고 싶은 작업을 명확하게 작성하면 더 정확한 워크플로우가 생성됩니다.
                  <br />
                  예: "네이버 증권에서 삼성전자 검색 후 스크린샷 저장"
                </p>
              </div>

              {videoDetail && (
                <div className="flex gap-2 text-xs text-muted-foreground">
                  <span>영상 길이: {videoDetail.duration}초</span>
                  <span>•</span>
                  <span>프레임 수: {videoDetail.frame_count}개</span>
                </div>
              )}
            </div>
          )}

          {status === "completed" && videoDetail && (
            <div className="space-y-4 py-2">
              <div className="flex items-center gap-3 p-4 bg-green-50 rounded-2xl">
                <div className="w-10 h-10 rounded-xl bg-green-500 flex items-center justify-center flex-shrink-0">
                  <CheckCircle className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="font-semibold text-sm text-green-800">분석 완료!</p>
                  <p className="text-xs text-green-700">
                    {videoDetail.generated_blocks?.length || 0}개 블록이 생성되었습니다
                  </p>
                </div>
              </div>

              {videoDetail.analysis_result && (
                <div className="space-y-3">
                  <div className="bg-secondary/50 rounded-xl p-4">
                    <h4 className="text-xs font-semibold mb-2">분석 결과</h4>
                    <p className="font-medium text-sm mb-1">{videoDetail.analysis_result.task_name}</p>
                    <p className="text-xs text-muted-foreground">{videoDetail.analysis_result.summary}</p>
                  </div>

                  {videoDetail.transcript && (
                    <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                      <h4 className="text-xs font-semibold mb-2 flex items-center gap-1.5 text-blue-800">
                        <FileText className="w-3.5 h-3.5" />
                        음성 인식 결과
                      </h4>
                      <div className="max-h-32 overflow-y-auto scrollbar-thin">
                        <p className="text-xs text-blue-700 whitespace-pre-wrap">{videoDetail.transcript}</p>
                      </div>
                      <p className="text-[10px] text-blue-500 mt-2">
                        총 {videoDetail.transcript.length}자
                      </p>
                    </div>
                  )}

                  <div className="flex gap-2 text-xs text-muted-foreground">
                    <span>영상 길이: {videoDetail.duration}초</span>
                    <span>•</span>
                    <span>프레임 수: {videoDetail.frame_count}개</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {status === "failed" && (
            <div className="space-y-4 py-4">
              <div className="flex items-center gap-3 p-4 bg-red-50 rounded-2xl">
                <div className="w-10 h-10 rounded-xl bg-red-500 flex items-center justify-center flex-shrink-0">
                  <AlertCircle className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="font-semibold text-sm text-red-800">처리 실패</p>
                  <p className="text-xs text-red-700">{errorMessage || "영상 처리 중 오류가 발생했습니다."}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t flex-shrink-0">
          <Button variant="ghost" className="rounded-xl" onClick={onClose}>
            {status === "completed" ? "닫기" : "취소"}
          </Button>
          {status === "idle" && (
            <Button
              className="rounded-xl px-6 gap-2"
              disabled={!selectedFile}
              onClick={handleUpload}
            >
              <Upload className="w-4 h-4" />
              분석 시작
            </Button>
          )}
          {status === "transcript_review" && (
            <Button
              className="rounded-xl px-6 gap-2"
              onClick={handleConfirmTranscript}
              disabled={!editedTranscript.trim()}
            >
              <CheckCircle className="w-4 h-4" />
              확인 및 계속
            </Button>
          )}
          {status === "completed" && videoDetail?.generated_blocks && (
            <Button className="rounded-xl px-6 gap-2" onClick={handleApplyBlocks}>
              <Play className="w-4 h-4" />
              워크스페이스에 추가
            </Button>
          )}
          {status === "failed" && (
            <Button className="rounded-xl px-6" onClick={resetState}>
              다시 시도
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
