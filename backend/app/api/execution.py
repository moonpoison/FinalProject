"""
코드 생성 및 실행 관련 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import os
import platform
from datetime import datetime

from app.models.user import User
from app.utils.security import get_current_user
from app.services.code_generator import code_generator

AGENT_VERSION = "1.0.0"
# backend/ 의 부모가 프로젝트 루트
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
AGENT_DIST_DIR = os.path.join(_PROJECT_ROOT, "agent", "dist")
AGENT_SCRIPT_DIR = os.path.join(_PROJECT_ROOT, "agent")

router = APIRouter()


class GenerateCodeRequest(BaseModel):
    blocks: List[Dict[str, Any]]
    workflow_name: Optional[str] = "automation"
    prompt: Optional[str] = None  # 원본 프롬프트 (지식베이스 참조용)


class ExecutionCommand(BaseModel):
    command_id: str
    command_type: str  # "run", "stop", "status"
    workflow_name: str
    blocks: Optional[List[Dict[str, Any]]] = None
    created_at: str


# 메모리 내 실행 큐 (실제 서비스에서는 Redis 등 사용)
execution_queue: Dict[str, ExecutionCommand] = {}
execution_results: Dict[str, Dict[str, Any]] = {}


@router.post("/generate-code")
async def generate_code(
    request: GenerateCodeRequest,
    current_user: User = Depends(get_current_user),
):
    """블록을 Python 코드로 변환 (지식베이스 참조)"""
    try:
        code = code_generator.generate(
            blocks=request.blocks,
            workflow_name=request.workflow_name,
            prompt=request.prompt  # 지식베이스 검색용
        )
        return {
            "success": True,
            "code": code,
            "block_count": len(request.blocks),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"코드 생성 실패: {str(e)}"
        )


@router.get("/download-code", response_class=PlainTextResponse)
async def download_code(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
):
    """생성된 코드 다운로드 (추후 워크스페이스 연동)"""
    # TODO: 워크스페이스에서 블록 가져오기
    return PlainTextResponse(
        content="# 워크스페이스 ID로 코드 생성 예정",
        media_type="text/x-python",
        headers={
            "Content-Disposition": f"attachment; filename={workflow_id}.py"
        }
    )


@router.post("/queue-execution")
async def queue_execution(
    request: GenerateCodeRequest,
    current_user: User = Depends(get_current_user),
):
    """로컬 에이전트용 실행 명령 큐에 추가"""
    command_id = str(uuid.uuid4())

    command = ExecutionCommand(
        command_id=command_id,
        command_type="run",
        workflow_name=request.workflow_name,
        blocks=request.blocks,
        created_at=datetime.utcnow().isoformat(),
    )

    execution_queue[command_id] = command

    return {
        "success": True,
        "command_id": command_id,
        "message": "실행 명령이 큐에 추가되었습니다. 로컬 에이전트가 실행합니다.",
    }


@router.get("/pending-commands")
async def get_pending_commands(
    agent_id: str,
):
    """로컬 에이전트가 대기 중인 명령 가져오기 (폴링)"""
    # 대기 중인 명령들 반환
    pending = list(execution_queue.values())

    # 반환 후 큐에서 제거 (단순 구현)
    for cmd in pending:
        del execution_queue[cmd.command_id]

    return {
        "commands": [cmd.model_dump() for cmd in pending],
        "count": len(pending),
    }


@router.post("/report-result")
async def report_result(
    command_id: str,
    success: bool,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
):
    """로컬 에이전트가 실행 결과 보고"""
    execution_results[command_id] = {
        "command_id": command_id,
        "success": success,
        "data": data,
        "error": error,
        "completed_at": datetime.utcnow().isoformat(),
    }

    return {"success": True, "message": "결과가 기록되었습니다."}


@router.get("/execution-status/{command_id}")
async def get_execution_status(
    command_id: str,
    current_user: User = Depends(get_current_user),
):
    """실행 상태 확인"""
    if command_id in execution_results:
        return execution_results[command_id]

    if command_id in execution_queue:
        return {
            "command_id": command_id,
            "status": "pending",
            "message": "에이전트 실행 대기 중",
        }

    return {
        "command_id": command_id,
        "status": "not_found",
        "message": "해당 명령을 찾을 수 없습니다.",
    }


# 현재 실행 중인 명령 추적
running_commands: Dict[str, bool] = {}  # command_id -> is_running
stop_requests: Dict[str, bool] = {}  # command_id -> stop_requested


@router.post("/stop-execution/{command_id}")
async def stop_execution(
    command_id: str,
    current_user: User = Depends(get_current_user),
):
    """실행 중인 자동화 중단 요청"""
    # 큐에서 제거 (아직 실행 안된 경우)
    if command_id in execution_queue:
        del execution_queue[command_id]
        return {
            "success": True,
            "message": "대기 중인 명령이 취소되었습니다.",
            "status": "cancelled"
        }

    # 실행 중인 경우 중단 요청 플래그 설정
    stop_requests[command_id] = True

    return {
        "success": True,
        "message": "중단 요청이 전송되었습니다. 에이전트가 중단합니다.",
        "status": "stop_requested"
    }


@router.get("/check-stop/{command_id}")
async def check_stop_request(command_id: str):
    """로컬 에이전트가 중단 요청 확인 (폴링)"""
    should_stop = stop_requests.get(command_id, False)

    # 확인 후 플래그 제거
    if should_stop and command_id in stop_requests:
        del stop_requests[command_id]

    return {
        "command_id": command_id,
        "should_stop": should_stop
    }


@router.post("/mark-running/{command_id}")
async def mark_running(command_id: str, is_running: bool = True):
    """로컬 에이전트가 실행 상태 업데이트"""
    if is_running:
        running_commands[command_id] = True
    else:
        running_commands.pop(command_id, None)

    return {"success": True, "is_running": is_running}


# ── 에이전트 배포 관련 ────────────────────────────────────────────

GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # 예: "username/RPA-main"

AGENT_FILENAMES = {
    "mac": "AutoFlowAgent-mac",
    "windows": "AutoFlowAgent-windows.exe",
    "linux": "AutoFlowAgent-linux",
}


@router.get("/agent/version")
async def get_agent_version():
    """에이전트 최신 버전 및 다운로드 URL 반환"""
    downloads = {}

    # 1. GitHub Releases 링크 (우선)
    if GITHUB_REPO:
        release_base = f"https://github.com/{GITHUB_REPO}/releases/latest/download"
        for plat, filename in AGENT_FILENAMES.items():
            downloads[plat] = f"{release_base}/{filename}"
    else:
        # 2. 로컬 빌드 파일 fallback
        for plat in ["mac", "windows", "linux"]:
            ext = ".exe" if plat == "windows" else ""
            filename = f"AutoFlowAgent-v{AGENT_VERSION}-{plat}{ext}"
            filepath = os.path.join(AGENT_DIST_DIR, filename)
            if os.path.exists(filepath):
                downloads[plat] = f"/api/execution/agent/download?platform={plat}"

    return {
        "version": AGENT_VERSION,
        "downloads": downloads,
        "github_repo": GITHUB_REPO or None,
    }


@router.get("/agent/download")
async def download_agent(
    platform_name: str = Query("auto", alias="platform"),
):
    """에이전트 바이너리 다운로드"""
    # auto 감지
    if platform_name == "auto":
        system = platform.system().lower()
        if system == "darwin":
            platform_name = "mac"
        elif system == "windows":
            platform_name = "windows"
        else:
            platform_name = "linux"

    ext = ".exe" if platform_name == "windows" else ""
    filename = f"AutoFlowAgent-v{AGENT_VERSION}-{platform_name}{ext}"
    filepath = os.path.join(AGENT_DIST_DIR, filename)

    if not os.path.exists(filepath):
        # 빌드 파일이 없으면 Python 스크립트 제공
        script_path = os.path.join(AGENT_SCRIPT_DIR, "ws_agent.py")
        if os.path.exists(script_path):
            return FileResponse(
                path=script_path,
                filename="AutoFlowAgent.py",
                media_type="text/x-python",
            )
        raise HTTPException(
            status_code=404,
            detail=f"{platform_name}용 에이전트 빌드가 아직 준비되지 않았습니다.",
        )

    media_type = "application/octet-stream"
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type=media_type,
    )
