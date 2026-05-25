"""
셀렉터 검증 API 라우터
실제 웹페이지에서 셀렉터 유효성 검증 및 추천
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import asyncio

from app.services.selector_validator import (
    selector_validator,
    validate_workflow_selectors
)

router = APIRouter(prefix="/validation", tags=["Validation"])


class SelectorInput(BaseModel):
    selector: str
    type: str = "css"  # "css" or "xpath"
    name: Optional[str] = None


class ValidateSelectorsRequest(BaseModel):
    url: str = Field(..., description="검증할 페이지 URL")
    selectors: List[SelectorInput] = Field(..., description="검증할 셀렉터 목록")


class ValidateWorkflowRequest(BaseModel):
    url: str = Field(..., description="검증할 페이지 URL")
    blocks: List[Dict[str, Any]] = Field(..., description="워크플로우 블록 목록")


class AnalyzePageRequest(BaseModel):
    url: str = Field(..., description="분석할 페이지 URL")


class SuggestSelectorsRequest(BaseModel):
    url: str = Field(..., description="대상 페이지 URL")
    action_type: str = Field(..., description="액션 타입: search, login, list, button, form")
    context: Optional[str] = Field(None, description="추가 컨텍스트 (예: '검색창', '로그인 버튼')")


@router.post("/selectors")
async def validate_selectors(request: ValidateSelectorsRequest):
    """
    여러 CSS/XPath 셀렉터를 실제 웹페이지에서 검증합니다.

    - 각 셀렉터가 페이지에 존재하는지 확인
    - 매칭되는 요소 개수 반환
    - 샘플 텍스트 제공
    - 실패 시 대안 셀렉터 제안
    """
    try:
        selectors = [
            {
                "selector": s.selector,
                "type": s.type,
                "name": s.name
            }
            for s in request.selectors
        ]

        result = await selector_validator.validate_selectors(
            url=request.url,
            selectors=selectors
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검증 실패: {str(e)}")


@router.post("/workflow")
async def validate_workflow(request: ValidateWorkflowRequest):
    """
    워크플로우의 모든 셀렉터를 한번에 검증합니다.

    - 블록에서 selector 필드를 자동 추출
    - 각 셀렉터의 유효성 검증
    - 블록별로 검증 결과 반환
    """
    try:
        result = await validate_workflow_selectors(
            url=request.url,
            blocks=request.blocks
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"워크플로우 검증 실패: {str(e)}")


@router.post("/analyze-page")
async def analyze_page(request: AnalyzePageRequest):
    """
    페이지 구조를 분석하여 자동화에 유용한 요소들을 추출합니다.

    - 폼, 입력 필드, 버튼 추출
    - 리스트/반복 요소 감지
    - 각 요소에 대한 CSS 셀렉터 생성
    """
    try:
        analysis = await selector_validator.analyze_page(request.url)

        if not analysis.fetch_success:
            return {
                "success": False,
                "error": analysis.error,
                "url": request.url
            }

        return {
            "success": True,
            "url": analysis.url,
            "title": analysis.title,
            "html_length": analysis.html_length,
            "elements": {
                "forms": analysis.forms,
                "inputs": analysis.inputs,
                "buttons": analysis.buttons,
                "lists": analysis.lists,
                "links": analysis.links
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"페이지 분석 실패: {str(e)}")


@router.post("/suggest-selectors")
async def suggest_selectors(request: SuggestSelectorsRequest):
    """
    특정 액션에 적합한 셀렉터를 추천합니다.

    - action_type: search, login, list, button, form
    - 페이지 분석 후 가장 적합한 셀렉터 추천
    - 신뢰도 점수 포함
    """
    try:
        suggestions = await selector_validator.suggest_selectors_for_action(
            url=request.url,
            action_type=request.action_type,
            context=request.context
        )

        return {
            "success": True,
            "url": request.url,
            "action_type": request.action_type,
            "suggestions": suggestions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"셀렉터 추천 실패: {str(e)}")


@router.get("/health")
async def health_check():
    """검증 서비스 상태 확인"""
    return {"status": "ok", "service": "selector_validator"}
