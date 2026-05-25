from pydantic import BaseModel
from typing import List, Optional, Any, Dict


class AIQuestion(BaseModel):
    """AI가 사용자에게 묻는 질문"""
    id: str
    question: str
    type: str = "choice"  # choice, text, confirm
    options: Optional[List[str]] = None
    default: Optional[str] = None
    hint: Optional[str] = None  # 질문에 대한 추가 설명/힌트
    required: bool = True  # 필수 질문 여부
    placeholder: Optional[str] = None  # text 타입 입력 필드 플레이스홀더


class AIConversationMessage(BaseModel):
    """대화 메시지"""
    role: str  # "user" or "assistant"
    content: str
    questions: Optional[List[AIQuestion]] = None
    answers: Optional[Dict[str, str]] = None


class AIConversationRequest(BaseModel):
    """대화형 AI 요청"""
    prompt: str
    conversation_history: Optional[List[AIConversationMessage]] = None
    answers: Optional[Dict[str, str]] = None  # 질문에 대한 답변
    questions: Optional[List[AIQuestion]] = None  # 답변 제출 시 질문 내용 포함


class AIConversationResponse(BaseModel):
    """대화형 AI 응답"""
    mode: str  # "questions" or "workflow"
    message: Optional[str] = None
    questions: Optional[List[AIQuestion]] = None
    workflow: Optional[dict] = None  # workflow가 생성된 경우
    reference_projects: Optional[List[dict]] = None  # 참조한 프로젝트들


class WorkflowStep(BaseModel):
    id: str
    label: str
    description: str
    block_type: str
    color: str
    icon: Optional[str] = None
    field_values: Optional[dict] = None  # 자동으로 채워질 필드 값들


class WorkflowGroup(BaseModel):
    id: str
    label: str
    description: str
    color: str
    steps: List[WorkflowStep]


class AIAnalyzeRequest(BaseModel):
    prompt: str


class AIAnalyzeResponse(BaseModel):
    task_name: str
    summary: str
    groups: List[WorkflowGroup]
    confidence: int


class BlockData(BaseModel):
    id: str
    type: str
    category: str
    label: str
    icon: str
    color: str
    fields: List[Any]
    instance_id: str
    field_values: dict
    group_id: Optional[str] = None
    group_label: Optional[str] = None
    group_color: Optional[str] = None


class AIGenerateBlocksRequest(BaseModel):
    groups: List[WorkflowGroup]


class AIGenerateBlocksResponse(BaseModel):
    blocks: List[BlockData]


class CodeVerificationIssue(BaseModel):
    """코드 검증 이슈"""
    severity: str  # "error", "warning", "info"
    block_id: Optional[str] = None  # 문제가 있는 블록 ID
    message: str  # 이슈 설명
    suggestion: Optional[str] = None  # 수정 제안


class CodeVerificationRequest(BaseModel):
    """코드 검증 요청"""
    workflow: dict
    original_prompt: str


class CodeVerificationResponse(BaseModel):
    """코드 검증 응답"""
    is_valid: bool  # 코드가 유효한지
    score: int  # 0-100 점수
    summary: str  # 검증 결과 요약
    issues: List[CodeVerificationIssue]  # 발견된 이슈들
    test_results: Optional[List[dict]] = None  # 테스트 결과
    improved_workflow: Optional[dict] = None  # 개선된 워크플로우 (issues가 있을 경우)
