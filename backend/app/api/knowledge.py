"""
Knowledge Base API - 자동화 지식베이스 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio

from app.models.user import User
from app.utils.security import get_current_user
from app.services.knowledge_base import KnowledgeBase, get_knowledge_base

router = APIRouter()


# === Request/Response Models ===

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResultItem(BaseModel):
    id: str
    name: str
    category: str
    subcategory: str
    sites: List[str]
    libraries: List[str]
    description: str
    score: float
    keyword_score: float
    semantic_score: float


class SearchResponse(BaseModel):
    success: bool
    count: int
    results: List[SearchResultItem]


class ProjectDetail(BaseModel):
    id: str
    name: str
    category: str
    subcategory: str
    sites: List[str]
    libraries: List[str]
    actions: List[str]
    selectors: List[str]
    description: str
    main_code: str
    file_count: int
    total_lines: int


class StatsResponse(BaseModel):
    total_projects: int
    total_lines: int
    categories: Dict[str, int]
    has_vector_db: bool


class BuildIndexResponse(BaseModel):
    success: bool
    message: str


class ContextRequest(BaseModel):
    prompt: str
    top_k: int = 3


class ContextResponse(BaseModel):
    found: bool
    count: int
    context: str
    references: List[Dict[str, Any]]


# === Endpoints ===

@router.get("/stats", response_model=StatsResponse)
async def get_stats(current_user: User = Depends(get_current_user)):
    """지식베이스 통계"""
    try:
        kb = get_knowledge_base()
        stats = kb.get_stats()
        return StatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"통계 조회 실패: {str(e)}"
        )


@router.post("/search", response_model=SearchResponse)
async def search_projects(
    request: SearchRequest,
    current_user: User = Depends(get_current_user)
):
    """프로젝트 검색"""
    try:
        kb = get_knowledge_base()
        results = kb.search(request.query, request.top_k)

        return SearchResponse(
            success=True,
            count=len(results),
            results=[
                SearchResultItem(
                    id=r.id,
                    name=r.name,
                    category=r.category,
                    subcategory=r.subcategory,
                    sites=r.sites,
                    libraries=r.libraries,
                    description=r.description,
                    score=r.score,
                    keyword_score=r.keyword_score,
                    semantic_score=r.semantic_score
                ) for r in results
            ]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"검색 실패: {str(e)}"
        )


@router.post("/context", response_model=ContextResponse)
async def get_ai_context(
    request: ContextRequest,
    current_user: User = Depends(get_current_user)
):
    """AI 워크플로우 생성을 위한 컨텍스트"""
    try:
        kb = get_knowledge_base()
        search_result = kb.search_for_workflow(request.prompt, request.top_k)
        context_str = kb.get_context_for_ai(request.prompt)

        return ContextResponse(
            found=search_result["found"],
            count=search_result.get("count", 0),
            context=context_str,
            references=search_result.get("references", [])
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"컨텍스트 생성 실패: {str(e)}"
        )


@router.get("/project/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """프로젝트 상세 조회"""
    try:
        kb = get_knowledge_base()
        project = kb.get_project_by_id(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="프로젝트를 찾을 수 없습니다"
            )

        return ProjectDetail(
            id=project["id"],
            name=project["name"],
            category=project["category"],
            subcategory=project["subcategory"],
            sites=project.get("sites", []),
            libraries=project.get("libraries", []),
            actions=project.get("actions", []),
            selectors=project.get("selectors", []),
            description=project.get("description", ""),
            main_code=project.get("main_code", ""),
            file_count=project.get("file_count", 0),
            total_lines=project.get("total_lines", 0)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"프로젝트 조회 실패: {str(e)}"
        )


@router.get("/category/{category}")
async def get_projects_by_category(
    category: str,
    current_user: User = Depends(get_current_user)
):
    """카테고리별 프로젝트 목록"""
    try:
        kb = get_knowledge_base()
        projects = kb.get_projects_by_category(category)

        return {
            "category": category,
            "count": len(projects),
            "projects": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "subcategory": p.get("subcategory", ""),
                    "description": p.get("description", "")
                } for p in projects
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"카테고리 조회 실패: {str(e)}"
        )


@router.get("/selectors/{site}")
async def get_site_selectors(
    site: str,
    current_user: User = Depends(get_current_user)
):
    """사이트별 주요 셀렉터 목록"""
    try:
        kb = get_knowledge_base()
        selectors = kb.get_selectors_for_site(site)

        return {
            "site": site,
            "count": len(selectors),
            "selectors": selectors
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"셀렉터 조회 실패: {str(e)}"
        )


@router.post("/build", response_model=BuildIndexResponse)
async def build_index(
    background_tasks: BackgroundTasks,
    force: bool = False,
    current_user: User = Depends(get_current_user)
):
    """인덱스 구축 (백그라운드)"""
    # 관리자 권한 체크 (필요시)
    # if current_user.role != "admin":
    #     raise HTTPException(status_code=403, detail="관리자만 실행 가능")

    def build_task():
        kb = get_knowledge_base()
        kb.build_index(force=force)

    background_tasks.add_task(build_task)

    return BuildIndexResponse(
        success=True,
        message="인덱스 구축이 백그라운드에서 시작되었습니다."
    )


@router.get("/categories")
async def get_all_categories(current_user: User = Depends(get_current_user)):
    """모든 카테고리 목록"""
    try:
        kb = get_knowledge_base()
        stats = kb.get_stats()

        categories = [
            {"name": name, "count": count}
            for name, count in sorted(
                stats["categories"].items(),
                key=lambda x: -x[1]
            )
        ]

        return {
            "total": len(categories),
            "categories": categories
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"카테고리 목록 조회 실패: {str(e)}"
        )
