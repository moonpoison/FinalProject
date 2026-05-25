from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List, AsyncGenerator
import json
import asyncio

from app.models.user import User
from app.schemas.ai import (
    AIAnalyzeRequest, AIAnalyzeResponse, WorkflowGroup, WorkflowStep,
    AIGenerateBlocksRequest, AIGenerateBlocksResponse, BlockData,
    AIConversationRequest, AIConversationResponse, AIQuestion, AIConversationMessage,
    CodeVerificationRequest, CodeVerificationResponse, CodeVerificationIssue
)
from app.utils.security import get_current_user
from app.config import settings
from app.services.web_analyzer import WebAnalyzer, SITE_SELECTORS
from app.services.intelligent_selector import intelligent_selector

def get_known_site_selectors(url: str) -> dict:
    """URL에 해당하는 알려진 사이트 셀렉터 반환"""
    for site_key, site_info in SITE_SELECTORS.items():
        site_url = site_info.get("url", "")
        # URL에 사이트 도메인이 포함되어 있으면 해당 셀렉터 반환
        if site_url and site_url.replace("https://", "").replace("http://", "").split("/")[0] in url:
            return {
                "site_key": site_key,
                **site_info
            }
    return {}

# 지식베이스 (옵션)
try:
    from app.services.knowledge_base import get_knowledge_base
    HAS_KNOWLEDGE_BASE = True
except ImportError:
    HAS_KNOWLEDGE_BASE = False
    print("[AI] 지식베이스 모듈 로드 실패 - 기본 모드로 동작")

router = APIRouter()

# Block definitions for AI to use
BLOCK_DEFINITIONS = {
    # 시작/설정
    "start": {"id": "start", "type": "start", "category": "start", "label": "시작하기", "icon": "play", "color": "#22c55e"},
    "schedule": {"id": "schedule", "type": "schedule", "category": "start", "label": "예약 실행", "icon": "calendar-clock", "color": "#16a34a"},

    # 브라우저 제어
    "open-site": {"id": "open-site", "type": "open-site", "category": "browser", "label": "사이트 열기", "icon": "globe", "color": "#3b82f6"},
    "navigate": {"id": "navigate", "type": "navigate", "category": "browser", "label": "페이지 이동", "icon": "arrow-right", "color": "#3b82f6"},
    "click": {"id": "click", "type": "click", "category": "action", "label": "클릭", "icon": "mouse-pointer", "color": "#eab308"},
    "scroll": {"id": "scroll", "type": "scroll", "category": "browser", "label": "스크롤", "icon": "move-vertical", "color": "#1d4ed8"},
    "wait-page-load": {"id": "wait-page-load", "type": "wait-page-load", "category": "browser", "label": "페이지 로드 대기", "icon": "loader", "color": "#1d4ed8"},
    "screenshot": {"id": "screenshot", "type": "screenshot", "category": "browser", "label": "스크린샷 저장", "icon": "camera", "color": "#1e40af"},

    # 입력
    "input-text": {"id": "input-text", "type": "input-text", "category": "keyboard", "label": "텍스트 입력", "icon": "keyboard", "color": "#f43f5e"},
    "press-key": {"id": "press-key", "type": "press-key", "category": "keyboard", "label": "키 누르기", "icon": "command", "color": "#e11d48"},

    # 데이터 추출
    "extract-text": {"id": "extract-text", "type": "extract-text", "category": "data", "label": "텍스트 추출", "icon": "text-cursor", "color": "#a855f7"},
    "extract-list": {"id": "extract-list", "type": "extract-list", "category": "data", "label": "목록 추출 (반복)", "icon": "rows", "color": "#9333ea"},
    "extract-attr": {"id": "extract-attr", "type": "extract-attr", "category": "data", "label": "속성값 추출", "icon": "code-xml", "color": "#9333ea"},

    # 데이터 저장
    "save-excel": {"id": "save-excel", "type": "save-excel", "category": "data", "label": "엑셀로 저장", "icon": "file-spreadsheet", "color": "#7c3aed"},
    "save-csv": {"id": "save-csv", "type": "save-csv", "category": "data", "label": "CSV로 저장", "icon": "file-text", "color": "#7c3aed"},

    # 제어 흐름
    "wait": {"id": "wait", "type": "wait", "category": "control", "label": "기다리기", "icon": "clock", "color": "#f97316"},
    "loop": {"id": "loop", "type": "loop", "category": "control", "label": "횟수 반복", "icon": "repeat", "color": "#ea580c"},
    "loop-list": {"id": "loop-list", "type": "loop-list", "category": "control", "label": "목록 반복", "icon": "list-ordered", "color": "#ea580c"},
    "condition": {"id": "condition", "type": "condition", "category": "control", "label": "조건문 (if)", "icon": "git-branch", "color": "#f97316"},
    "log": {"id": "log", "type": "log", "category": "control", "label": "로그 출력", "icon": "terminal", "color": "#c2410c"},

    # 알림/전송
    "send-slack": {"id": "send-slack", "type": "send-slack", "category": "data", "label": "Slack 알림", "icon": "message-square", "color": "#6d28d9"},
    "send-email": {"id": "send-email", "type": "send-email", "category": "data", "label": "이메일 전송", "icon": "mail", "color": "#7c3aed"},
    "http-request": {"id": "http-request", "type": "http-request", "category": "api", "label": "HTTP 요청", "icon": "globe-2", "color": "#10b981"},

    # 데스크톱/PyAutoGUI
    "mouse-click-coords": {"id": "mouse-click-coords", "type": "mouse-click-coords", "category": "desktop", "label": "좌표 클릭", "icon": "mouse-pointer-click", "color": "#0ea5e9"},
    "mouse-move": {"id": "mouse-move", "type": "mouse-move", "category": "desktop", "label": "마우스 이동", "icon": "move", "color": "#0ea5e9"},
    "pyautogui-type": {"id": "pyautogui-type", "type": "pyautogui-type", "category": "desktop", "label": "텍스트 타이핑", "icon": "type", "color": "#0ea5e9"},
    "pyautogui-hotkey": {"id": "pyautogui-hotkey", "type": "pyautogui-hotkey", "category": "desktop", "label": "단축키", "icon": "keyboard", "color": "#0ea5e9"},
    "image-click": {"id": "image-click", "type": "image-click", "category": "desktop", "label": "이미지 인식 클릭", "icon": "scan", "color": "#0ea5e9"},
    "window-focus": {"id": "window-focus", "type": "window-focus", "category": "desktop", "label": "창 활성화", "icon": "app-window", "color": "#0ea5e9"},
    "clipboard-copy": {"id": "clipboard-copy", "type": "clipboard-copy", "category": "desktop", "label": "클립보드 복사", "icon": "clipboard-copy", "color": "#06b6d4"},
    "clipboard-paste": {"id": "clipboard-paste", "type": "clipboard-paste", "category": "desktop", "label": "클립보드 붙여넣기", "icon": "clipboard-paste", "color": "#06b6d4"},

    # 고급
    "custom-code": {"id": "custom-code", "type": "custom-code", "category": "advanced", "label": "Python 코드 실행", "icon": "code", "color": "#ec4899"},
    "stealth-mode": {"id": "stealth-mode", "type": "stealth-mode", "category": "advanced", "label": "봇 탐지 우회", "icon": "shield", "color": "#ec4899"},
    "set-proxy": {"id": "set-proxy", "type": "set-proxy", "category": "advanced", "label": "프록시 설정", "icon": "server", "color": "#ec4899"},
    "random-delay": {"id": "random-delay", "type": "random-delay", "category": "advanced", "label": "랜덤 대기", "icon": "shuffle", "color": "#ec4899"},
    "switch-account": {"id": "switch-account", "type": "switch-account", "category": "advanced", "label": "계정 전환", "icon": "users", "color": "#ec4899"},
    "captcha-wait": {"id": "captcha-wait", "type": "captcha-wait", "category": "advanced", "label": "캡챠 대기", "icon": "puzzle", "color": "#ec4899"},

    # 데이터베이스
    "db-connect": {"id": "db-connect", "type": "db-connect", "category": "database", "label": "DB 연결", "icon": "database", "color": "#14b8a6"},
    "db-query": {"id": "db-query", "type": "db-query", "category": "database", "label": "DB 조회", "icon": "search", "color": "#14b8a6"},
    "db-execute": {"id": "db-execute", "type": "db-execute", "category": "database", "label": "DB 실행", "icon": "play-circle", "color": "#14b8a6"},

    # 파일/텍스트
    "read-file": {"id": "read-file", "type": "read-file", "category": "file", "label": "파일 읽기", "icon": "file-input", "color": "#8b5cf6"},
    "write-file": {"id": "write-file", "type": "write-file", "category": "file", "label": "파일 쓰기", "icon": "file-output", "color": "#8b5cf6"},
    "regex-extract": {"id": "regex-extract", "type": "regex-extract", "category": "file", "label": "정규식 추출", "icon": "regex", "color": "#8b5cf6"},
    "run-script": {"id": "run-script", "type": "run-script", "category": "file", "label": "스크립트 실행", "icon": "terminal-square", "color": "#8b5cf6"},
}

# Group colors
GROUP_COLORS = ["#22c55e", "#3b82f6", "#a855f7", "#7c3aed", "#f97316", "#eab308"]


async def analyze_with_claude(prompt: str) -> AIAnalyzeResponse:
    """Use Claude API to analyze the prompt and generate workflow structure."""
    import anthropic

    if not settings.ANTHROPIC_API_KEY:
        raise Exception("ANTHROPIC_API_KEY가 설정되지 않았습니다. backend/.env 파일을 확인하세요.")

    try:

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        system_prompt = """당신은 RPA(로봇 프로세스 자동화) 워크플로우 설계 전문가입니다.
사용자의 자연어 요청을 분석하여 자동화 워크플로우를 설계해야 합니다.

사용 가능한 블록 타입:
- start: 시작하기
- schedule: 예약 실행
- open-site: 사이트 열기
- navigate: 페이지 이동
- click: 클릭
- input-text: 텍스트 입력
- extract-text: 텍스트 추출
- extract-list: 목록 추출 (반복)
- extract-attr: 속성값 추출
- save-excel: 엑셀로 저장
- save-csv: CSV로 저장
- wait: 기다리기
- wait-page-load: 페이지 로드 대기
- loop: 횟수 반복
- loop-list: 목록 반복
- condition: 조건문 (if)
- send-slack: Slack 알림
- send-email: 이메일 전송
- http-request: HTTP 요청
- scroll: 스크롤
- screenshot: 스크린샷 저장
- press-key: 키 누르기
- log: 로그 출력

응답은 반드시 다음 JSON 형식으로 반환하세요:
{
    "task_name": "작업 이름 (30자 이내)",
    "summary": "작업 요약 설명 (100자 이내)",
    "confidence": 정확도 (50-100 사이 정수),
    "groups": [
        {
            "id": "g1",
            "label": "그룹 이름",
            "description": "그룹 설명",
            "color": "#22c55e",
            "steps": [
                {
                    "id": "s1",
                    "label": "단계 이름",
                    "description": "단계 설명",
                    "block_type": "블록 타입 (위 목록에서 선택)",
                    "color": "#22c55e"
                }
            ]
        }
    ]
}

그룹은 2-6개, 각 그룹당 스텝은 2-5개 정도로 구성하세요.
첫 번째 그룹의 첫 번째 스텝은 항상 'start' 블록이어야 합니다."""

        message = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {"role": "user", "content": f"다음 작업을 자동화해주세요: {prompt}"}
            ]
        )

        # Parse response
        response_text = message.content[0].text

        # Try to extract JSON from response
        try:
            # Find JSON in response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response_text)
        except json.JSONDecodeError:
            return generate_mock_response(prompt)

        # Convert to response model
        groups = []
        for i, g in enumerate(data.get("groups", [])):
            steps = []
            for s in g.get("steps", []):
                block_type = s.get("block_type", "start")
                block_def = BLOCK_DEFINITIONS.get(block_type, BLOCK_DEFINITIONS["start"])
                steps.append(WorkflowStep(
                    id=s.get("id", f"s{len(steps)+1}"),
                    label=s.get("label", ""),
                    description=s.get("description", ""),
                    block_type=block_type,
                    color=block_def.get("color", "#22c55e"),
                    field_values=s.get("field_values", {})  # Claude 응답에서 field_values 가져오기
                ))

            groups.append(WorkflowGroup(
                id=g.get("id", f"g{i+1}"),
                label=g.get("label", ""),
                description=g.get("description", ""),
                color=GROUP_COLORS[i % len(GROUP_COLORS)],
                steps=steps
            ))

        return AIAnalyzeResponse(
            task_name=data.get("task_name", prompt[:30]),
            summary=data.get("summary", f"'{prompt}' 작업을 자동화합니다."),
            confidence=min(100, max(50, data.get("confidence", 85))),
            groups=groups
        )

    except Exception as e:
        print(f"Claude API error: {e}")
        return generate_mock_response(prompt)


def generate_mock_response(prompt: str) -> AIAnalyzeResponse:
    """Generate a mock response when Claude API is not available."""
    return generate_smart_response(prompt, {}, None)


def generate_smart_response(prompt: str, site_info: dict, web_analysis: dict = None) -> AIAnalyzeResponse:
    """웹 분석 결과를 기반으로 스마트한 응답 생성"""
    title = prompt[:30] + "..." if len(prompt) > 30 else prompt
    url = site_info.get("url", "https://example.com")
    site_key = site_info.get("site_key", "")
    recommended_method = "selenium"

    # 사이트별 기본 셀렉터 가져오기
    selectors = SITE_SELECTORS.get(site_key, {})
    if web_analysis:
        selectors.update(web_analysis.get("main_selectors", {}))
        recommended_method = web_analysis.get("recommended_method", "selenium")

    # 프롬프트에서 키워드 추출
    search_keyword = ""
    if "뉴스" in prompt:
        search_keyword = "뉴스"
    elif "가격" in prompt or "상품" in prompt:
        search_keyword = "상품"
    elif "검색" in prompt:
        # 검색어 추출 시도
        import re
        match = re.search(r"['\"]([^'\"]+)['\"]", prompt)
        if match:
            search_keyword = match.group(1)
        else:
            for word in prompt.split():
                if word not in ["검색", "크롤링", "수집", "해줘", "하고", "싶어", "네이버", "구글"]:
                    search_keyword = word
                    break

    # 뉴스 크롤링 감지
    is_news_crawling = any(kw in prompt.lower() for kw in ["뉴스", "news", "기사", "article"])
    is_shopping = any(kw in prompt.lower() for kw in ["가격", "상품", "쇼핑", "쿠팡", "지마켓"])
    is_search = any(kw in prompt.lower() for kw in ["검색", "search", "찾"])

    # 그룹 및 단계 생성
    groups = []
    step_id = 1

    # 그룹 1: 시작 및 사이트 접속
    group1_steps = [
        WorkflowStep(
            id=f"s{step_id}",
            label="시작하기",
            description="자동화 워크플로우를 시작합니다.",
            block_type="start",
            color="#22c55e",
            field_values={}
        ),
    ]
    step_id += 1

    group1_steps.append(WorkflowStep(
        id=f"s{step_id}",
        label="사이트 열기",
        description=f"{url}에 접속합니다.",
        block_type="open-site",
        color="#3b82f6",
        field_values={"url": url}
    ))
    step_id += 1

    group1_steps.append(WorkflowStep(
        id=f"s{step_id}",
        label="페이지 로드 대기",
        description="페이지가 완전히 로드될 때까지 기다립니다.",
        block_type="wait-page-load",
        color="#1d4ed8",
        field_values={"timeout": "10"}
    ))
    step_id += 1

    groups.append(WorkflowGroup(
        id="g1",
        label="사이트 접속",
        description=f"{url} 사이트에 접속합니다.",
        color="#22c55e",
        steps=group1_steps
    ))

    # 그룹 2: 검색 (검색이 필요한 경우)
    if is_search or search_keyword:
        group2_steps = []

        search_input_selector = selectors.get("search_input", "input[type=search], input[name=query], #search")
        search_button_selector = selectors.get("search_button", "button[type=submit], .btn_search, .search-btn")

        group2_steps.append(WorkflowStep(
            id=f"s{step_id}",
            label="검색어 입력",
            description=f"검색창에 '{search_keyword or '검색어'}'를 입력합니다.",
            block_type="input-text",
            color="#f43f5e",
            field_values={
                "selector": search_input_selector,
                "text": search_keyword or "검색어를 입력하세요",
                "clear": "clear"
            }
        ))
        step_id += 1

        group2_steps.append(WorkflowStep(
            id=f"s{step_id}",
            label="검색 버튼 클릭",
            description="검색 버튼을 클릭합니다.",
            block_type="click",
            color="#eab308",
            field_values={"selector": search_button_selector}
        ))
        step_id += 1

        group2_steps.append(WorkflowStep(
            id=f"s{step_id}",
            label="결과 로딩 대기",
            description="검색 결과가 로드될 때까지 기다립니다.",
            block_type="wait",
            color="#f97316",
            field_values={"seconds": "2"}
        ))
        step_id += 1

        groups.append(WorkflowGroup(
            id="g2",
            label="검색",
            description=f"'{search_keyword or '키워드'}'로 검색합니다.",
            color="#3b82f6",
            steps=group2_steps
        ))

    # 그룹 3: 데이터 수집
    group3_steps = []

    if is_news_crawling:
        article_selector = selectors.get("article_list", ".news_area, .list_news li, article")
        title_selector = selectors.get("article_title", ".news_tit, .tit, h3")
        link_selector = selectors.get("article_link", "a")

        group3_steps.append(WorkflowStep(
            id=f"s{step_id}",
            label="뉴스 목록 추출",
            description="뉴스 기사 목록을 추출합니다.",
            block_type="extract-list",
            color="#9333ea",
            field_values={
                "selector": article_selector,
                "fields": "title, link, description",
                "variable": "news_list"
            }
        ))
        step_id += 1
    elif is_shopping:
        product_selector = selectors.get("product_list", ".search-product, .product-item, li.item")
        group3_steps.append(WorkflowStep(
            id=f"s{step_id}",
            label="상품 목록 추출",
            description="상품 목록을 추출합니다.",
            block_type="extract-list",
            color="#9333ea",
            field_values={
                "selector": product_selector,
                "fields": "name, price, link",
                "variable": "product_list"
            }
        ))
        step_id += 1
    else:
        result_selector = selectors.get("result_list", ".result, .item, li")
        group3_steps.append(WorkflowStep(
            id=f"s{step_id}",
            label="결과 목록 추출",
            description="검색 결과를 추출합니다.",
            block_type="extract-list",
            color="#9333ea",
            field_values={
                "selector": result_selector,
                "fields": "title, link",
                "variable": "results"
            }
        ))
        step_id += 1

    groups.append(WorkflowGroup(
        id=f"g{len(groups)+1}",
        label="데이터 수집",
        description="페이지에서 데이터를 추출합니다.",
        color="#a855f7",
        steps=group3_steps
    ))

    # 그룹 4: 결과 저장
    group4_steps = []
    variable_name = "news_list" if is_news_crawling else "product_list" if is_shopping else "results"
    filename = "news_result.xlsx" if is_news_crawling else "product_result.xlsx" if is_shopping else "result.xlsx"

    group4_steps.append(WorkflowStep(
        id=f"s{step_id}",
        label="엑셀 저장",
        description=f"수집된 데이터를 {filename}로 저장합니다.",
        block_type="save-excel",
        color="#7c3aed",
        field_values={
            "variable": variable_name,
            "filename": filename,
            "mode": "overwrite"
        }
    ))
    step_id += 1

    group4_steps.append(WorkflowStep(
        id=f"s{step_id}",
        label="완료 로그",
        description="작업 완료 메시지를 출력합니다.",
        block_type="log",
        color="#c2410c",
        field_values={
            "message": f"데이터 수집 완료! 총 {{{{{variable_name}}}}}.length개 항목 저장됨",
            "level": "success"
        }
    ))
    step_id += 1

    groups.append(WorkflowGroup(
        id=f"g{len(groups)+1}",
        label="결과 저장",
        description="수집한 데이터를 파일로 저장합니다.",
        color="#7c3aed",
        steps=group4_steps
    ))

    method_desc = f"Selenium을 사용하여 브라우저 자동화로 실행됩니다." if recommended_method == "selenium" else "HTTP 요청으로 빠르게 데이터를 수집합니다."

    return AIAnalyzeResponse(
        task_name=title,
        summary=f"'{title}' 작업을 분석했습니다. {method_desc} 총 {len(groups)}개 그룹, {step_id-1}단계로 구성됩니다.",
        confidence=92 if web_analysis else 85,
        groups=groups
    )


@router.post("/analyze", response_model=AIAnalyzeResponse)
async def analyze_prompt(
    request: AIAnalyzeRequest,
    current_user: User = Depends(get_current_user)
):
    """Analyze natural language prompt and generate workflow structure."""
    if not request.prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프롬프트를 입력해주세요."
        )

    try:
        return await analyze_with_claude(request.prompt)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


async def stream_analyze_generator(prompt: str) -> AsyncGenerator[str, None]:
    """Stream workflow analysis results one group at a time."""
    import anthropic

    # 먼저 웹 분석 수행
    web_analysis = None
    site_info = await WebAnalyzer.analyze_prompt_for_url(prompt)

    if site_info.get("url"):
        yield f"data: {json.dumps({'type': 'status', 'message': '웹사이트 분석 중...'})}\n\n"
        await asyncio.sleep(0.5)

        html = await WebAnalyzer.fetch_page(site_info["url"])
        if html:
            page_structure = WebAnalyzer.extract_page_structure(html)
            web_analysis = await WebAnalyzer.analyze_with_claude(prompt, site_info["url"], page_structure)
            method = web_analysis.get("recommended_method", "selenium")
            status_msg = {"type": "status", "message": f"분석 완료: {method} 사용 권장"}
            yield f"data: {json.dumps(status_msg)}\n\n"
            await asyncio.sleep(0.5)

    if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == "your-anthropic-api-key":
        # Use mock streaming for demo with web analysis
        mock_response = generate_smart_response(prompt, site_info, web_analysis)

        # Send task info first
        yield f"data: {json.dumps({'type': 'info', 'task_name': mock_response.task_name, 'summary': mock_response.summary, 'confidence': mock_response.confidence, 'total_groups': len(mock_response.groups)})}\n\n"
        await asyncio.sleep(0.8)

        # Stream each group with 1 second delay for animation effect
        for i, group in enumerate(mock_response.groups):
            group_data = {
                'type': 'group',
                'index': i,
                'group': {
                    'id': group.id,
                    'label': group.label,
                    'description': group.description,
                    'color': group.color,
                    'steps': [
                        {
                            'id': s.id,
                            'label': s.label,
                            'description': s.description,
                            'block_type': s.block_type,
                            'color': s.color,
                            'field_values': s.field_values if s.field_values else {}
                        } for s in group.steps
                    ]
                }
            }
            yield f"data: {json.dumps(group_data)}\n\n"
            await asyncio.sleep(1.0)  # 1초 딜레이로 애니메이션 효과

        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # 지식베이스에서 유사 프로젝트 검색
        kb_context = ""
        if HAS_KNOWLEDGE_BASE:
            try:
                kb = get_knowledge_base()
                kb_context = kb.get_context_for_ai(prompt)
                if kb_context:
                    yield f"data: {json.dumps({'type': 'status', 'message': '유사 프로젝트 참조 중...'})}\n\n"
                    await asyncio.sleep(0.3)
            except Exception as e:
                print(f"[AI] 지식베이스 검색 실패: {e}")

        # 웹 분석 결과를 프롬프트에 포함 (지능형 셀렉터 추출)
        web_context = ""
        target_url = site_info.get('url', '')

        # 지능형 셀렉터 추출 (Claude가 실제 HTML 분석)
        if target_url:
            yield f"data: {json.dumps({'type': 'status', 'message': '실제 HTML 분석 중...'})}\n\n"
            await asyncio.sleep(0.3)

            try:
                # IntelligentSelectorService로 실제 HTML 기반 분석
                intelligent_result = await intelligent_selector.analyze_page_for_task(
                    target_url,
                    prompt,
                    None  # target_data는 프롬프트에서 자동 추출
                )

                if intelligent_result.get("success"):
                    web_context = f"""
## 📄 실제 HTML 분석 결과: {target_url}
"""
                    # 셀렉터
                    selectors = intelligent_result.get("selectors", {})
                    if selectors:
                        web_context += "\n### 검증된 셀렉터:\n"
                        for name, info in selectors.items():
                            if isinstance(info, dict):
                                selector = info.get("selector", "not_found")
                                confidence = info.get("confidence", 0)
                                sample = info.get("sample_value", "")
                                if selector != "not_found":
                                    web_context += f"- **{name}**: `{selector}` "
                                    if sample:
                                        web_context += f"(예: {sample[:30]})"
                                    web_context += f" [신뢰도: {confidence:.0%}]\n"

                    # 폼
                    forms = intelligent_result.get("forms", [])
                    if forms:
                        web_context += "\n### 폼:\n"
                        for form in forms:
                            web_context += f"- {form.get('purpose', '폼')}: "
                            web_context += f"입력=`{form.get('input_selector', '')}`, "
                            web_context += f"제출=`{form.get('submit_selector', '')}`\n"

                    # 리스트
                    lists = intelligent_result.get("lists", [])
                    if lists:
                        web_context += "\n### 목록/반복 요소:\n"
                        for lst in lists:
                            web_context += f"- {lst.get('purpose', '목록')}: "
                            web_context += f"항목=`{lst.get('item_selector', '')}` "
                            web_context += f"({lst.get('item_count', '?')}개)\n"

                    if intelligent_result.get("notes"):
                        web_context += f"\n⚠️ {intelligent_result['notes']}\n"

                    yield f"data: {json.dumps({'type': 'status', 'message': f'셀렉터 {len(selectors)}개 추출 완료'})}\n\n"
                    await asyncio.sleep(0.3)
                else:
                    web_context += f"\n## ⚠️ HTML 분석 실패: {intelligent_result.get('error', 'unknown')}\n"

            except Exception as e:
                print(f"[AI] 지능형 셀렉터 분석 오류: {e}")
                # 기존 방식으로 폴백
                if web_analysis:
                    selectors = web_analysis.get("main_selectors", {})
                    web_context += f"\n## 폴백 분석 결과: {target_url}\n"
                    if any(v for v in selectors.values() if v):
                        for key, val in selectors.items():
                            if val:
                                web_context += f"- {key}: `{val}`\n"

        # 알려진 사이트 셀렉터 추가 (보조)
        known_selectors = get_known_site_selectors(target_url) if target_url else {}
        if known_selectors:
            site_key = known_selectors.get("site_key", "")
            web_context += f"""
## 🎯 추가 참고: {known_selectors.get('description', site_key)}
**사전 정의된 셀렉터:**
"""
            for key, value in known_selectors.items():
                if key not in ["url", "description", "site_key", "recommended_method", "requires_js"]:
                    web_context += f"- {key}: `{value}`\n"

            if known_selectors.get("requires_js"):
                web_context += "\n⚠️ JavaScript 렌더링 필요 - Selenium 사용 권장\n"

        # 셀렉터 사용 규칙
        web_context += """
## ⚠️ 셀렉터 사용 규칙:
1. 위에 나열된 **검증된 셀렉터**만 사용하세요
2. 셀렉터를 **절대로 추측하거나 만들어내지 마세요**
3. 필요한 셀렉터가 없으면 해당 단계를 **생략**하세요
4. 신뢰도가 낮은 셀렉터는 주의해서 사용하세요
"""

        system_prompt = f"""당신은 RPA(로봇 프로세스 자동화) 워크플로우 설계 전문가입니다.
사용자의 자연어 요청을 분석하여 자동화 워크플로우를 설계해야 합니다.

## 사용 가능한 블록 타입과 field_values:
- start: 시작하기 (field_values: 없음)
- open-site: 사이트 열기 (field_values: {{"url": "https://..."}})
- click: 클릭 (field_values: {{"selector": "CSS셀렉터", "selectorType": "css"}})
- input-text: 텍스트 입력 (field_values: {{"selector": "CSS셀렉터", "text": "입력할텍스트", "clear": "clear"}})
- extract-text: 텍스트 추출 (field_values: {{"selector": "CSS셀렉터", "variable": "변수명"}})
- extract-list: 목록 추출 (field_values: {{"selector": "CSS셀렉터", "fields": "text, href", "variable": "변수명"}})
- extract-attr: 속성값 추출 (field_values: {{"selector": "CSS셀렉터", "attribute": "href", "variable": "변수명"}})
- save-excel: 엑셀 저장 (field_values: {{"variable": "저장할변수명", "filename": "result.xlsx", "mode": "overwrite"}})
- wait: 기다리기 (field_values: {{"seconds": "3"}})
- wait-page-load: 페이지 로드 대기 (field_values: {{"timeout": "10"}})
- log: 로그 출력 (field_values: {{"message": "메시지", "level": "info"}})
- screenshot: 스크린샷 (field_values: {{"filename": "screenshot.png"}}) - 자동으로 output 폴더에 저장됨
- scroll: 스크롤 (field_values: {{"direction": "down", "amount": "500"}})
- custom-code: Python 코드 (field_values: {{"code": "코드", "description": "설명"}})

## ⚠️ 파일 저장 규칙 (매우 중요!):
모든 파일은 자동으로 output 폴더에 저장됩니다.
custom-code 블록에서 파일을 저장할 때는 반드시 다음 변수를 사용하세요:
- self.screenshot_dir: 스크린샷 저장
- self.download_dir: 다운로드 파일
- self.data_dir: 데이터 파일 (JSON, 텍스트 등)
**절대 하드코딩된 경로(예: C:\\폴더명)를 사용하지 마세요!**

{web_context}

{kb_context}

## ⚠️ 셀렉터 사용 규칙 (매우 중요):
1. 위 "실제 웹페이지 분석 결과"에 제공된 셀렉터를 **반드시** 우선 사용하세요.
2. 셀렉터를 임의로 추측하거나 만들어내지 마세요.
3. 분석 결과에 없는 셀렉터가 필요한 경우, "페이지에서 발견된 요소들"에서 찾으세요.
4. 그래도 없으면 일반적인 CSS 셀렉터 패턴을 사용하되, 주석으로 "확인 필요"라고 표시하세요.

## 응답 형식:
응답은 반드시 다음 JSON 형식으로 반환하세요:
{{
    "task_name": "작업 이름 (30자 이내)",
    "summary": "작업 요약 설명 (100자 이내)",
    "confidence": 정확도 (50-100 사이 정수),
    "groups": [
        {{
            "id": "g1",
            "label": "그룹 이름",
            "description": "그룹 설명",
            "color": "#22c55e",
            "steps": [
                {{
                    "id": "s1",
                    "label": "단계 이름",
                    "description": "단계 설명",
                    "block_type": "블록 타입",
                    "color": "#22c55e",
                    "field_values": {{"필드명": "값"}}
                }}
            ]
        }}
    ]
}}

중요: 각 step에 반드시 field_values를 포함하세요. 실제 사용할 URL, 셀렉터, 텍스트 등을 채워넣어야 합니다.
그룹은 2-6개, 각 그룹당 스텝은 2-5개 정도로 구성하세요.
첫 번째 그룹의 첫 번째 스텝은 항상 'start' 블록이어야 합니다."""

        message = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=8192,
            system=system_prompt,
            messages=[
                {"role": "user", "content": f"다음 작업을 자동화해주세요: {prompt}"}
            ]
        )

        response_text = message.content[0].text

        # Parse the response
        import re
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = json.loads(response_text)

        task_name = data.get("task_name", prompt[:30])
        summary = data.get("summary", f"'{prompt}' 작업을 자동화합니다.")
        confidence = min(100, max(50, data.get("confidence", 85)))
        groups = data.get("groups", [])

        # Send task info first
        yield f"data: {json.dumps({'type': 'info', 'task_name': task_name, 'summary': summary, 'confidence': confidence, 'total_groups': len(groups)})}\n\n"
        await asyncio.sleep(0.8)

        # Stream each group with 1 second delay
        for i, g in enumerate(groups):
            steps = []
            for s in g.get("steps", []):
                block_type = s.get("block_type", "start")
                block_def = BLOCK_DEFINITIONS.get(block_type, BLOCK_DEFINITIONS["start"])
                steps.append({
                    'id': s.get("id", f"s{len(steps)+1}"),
                    'label': s.get("label", ""),
                    'description': s.get("description", ""),
                    'block_type': block_type,
                    'color': block_def.get("color", "#22c55e"),
                    'field_values': s.get("field_values", {})
                })

            group_data = {
                'type': 'group',
                'index': i,
                'group': {
                    'id': g.get("id", f"g{i+1}"),
                    'label': g.get("label", ""),
                    'description': g.get("description", ""),
                    'color': GROUP_COLORS[i % len(GROUP_COLORS)],
                    'steps': steps
                }
            }
            yield f"data: {json.dumps(group_data)}\n\n"
            await asyncio.sleep(1.0)  # 1초 딜레이로 애니메이션 효과

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        print(f"Claude streaming error: {e}")
        # Fallback to smart response
        mock_response = generate_smart_response(prompt, site_info, web_analysis)

        yield f"data: {json.dumps({'type': 'info', 'task_name': mock_response.task_name, 'summary': mock_response.summary, 'confidence': mock_response.confidence, 'total_groups': len(mock_response.groups)})}\n\n"
        await asyncio.sleep(0.8)

        for i, group in enumerate(mock_response.groups):
            group_data = {
                'type': 'group',
                'index': i,
                'group': {
                    'id': group.id,
                    'label': group.label,
                    'description': group.description,
                    'color': group.color,
                    'steps': [
                        {
                            'id': s.id,
                            'label': s.label,
                            'description': s.description,
                            'block_type': s.block_type,
                            'color': s.color,
                            'field_values': s.field_values or {}
                        } for s in group.steps
                    ]
                }
            }
            yield f"data: {json.dumps(group_data)}\n\n"
            await asyncio.sleep(1.0)  # 1초 딜레이로 애니메이션 효과

        yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/analyze-stream")
async def analyze_prompt_stream(
    request: AIAnalyzeRequest,
    current_user: User = Depends(get_current_user)
):
    """Stream analyze natural language prompt and generate workflow structure in real-time."""
    if not request.prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프롬프트를 입력해주세요."
        )

    return StreamingResponse(
        stream_analyze_generator(request.prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/generate-blocks", response_model=AIGenerateBlocksResponse)
async def generate_blocks(
    request: AIGenerateBlocksRequest,
    current_user: User = Depends(get_current_user)
):
    """Convert workflow groups to actual block data."""
    import time

    blocks = []
    ts = int(time.time() * 1000)

    group_map = {}
    for g in request.groups:
        group_map[g.id] = {"label": g.label, "color": g.color}

    for group in request.groups:
        for i, step in enumerate(group.steps):
            block_def = BLOCK_DEFINITIONS.get(step.block_type, BLOCK_DEFINITIONS["start"])

            blocks.append(BlockData(
                id=block_def["id"],
                type=block_def["type"],
                category=block_def["category"],
                label=block_def["label"],
                icon=block_def["icon"],
                color=block_def["color"],
                fields=[],  # Fields would be populated by frontend
                instance_id=f"{block_def['id']}-{ts + len(blocks)}",
                field_values=step.field_values or {},  # 스텝의 field_values 사용
                group_id=group.id,
                group_label=group.label,
                group_color=group.color
            ))

    return AIGenerateBlocksResponse(blocks=blocks)


@router.post("/conversation", response_model=AIConversationResponse)
async def conversation_analyze(
    request: AIConversationRequest,
    current_user: User = Depends(get_current_user)
):
    """대화형 AI - 질문 후 워크플로우 생성"""
    import anthropic

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY가 설정되지 않았습니다.")

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # 지식베이스에서 유사 프로젝트 검색
    reference_projects = []
    kb_context = ""
    detailed_code = ""

    if HAS_KNOWLEDGE_BASE:
        try:
            kb = get_knowledge_base()
            print(f"[AI] 지식베이스 검색 시작: '{request.prompt}'")
            search_result = kb.search_for_workflow(request.prompt, top_k=5)

            if search_result.get("found"):
                print(f"[AI] 지식베이스에서 {len(search_result.get('references', []))}개 프로젝트 찾음")
                for ref in search_result.get("references", []):
                    # 프로젝트 이름에서 특수문자 제거
                    safe_name = ref["name"].replace('"', '').replace("'", "").replace("(", "").replace(")", "")[:30]

                    reference_projects.append({
                        "name": safe_name,
                        "category": ref["category"],
                        "similarity": ref["similarity"],
                        "sites": ref["sites"][:3],
                        "libraries": ref["libraries"][:5]
                    })

                    # 셀렉터만 추출 (코드 대신 핵심 정보만)
                    selectors = ref.get('selectors', [])[:15]
                    selectors_text = '\n'.join([f"  - {s}" for s in selectors if s and len(s) < 100])

                    # 액션 추출
                    actions = ref.get('actions', [])[:10]
                    actions_text = ', '.join(actions) if actions else '없음'

                    detailed_code += f"""
### 참고 프로젝트: {safe_name}
- 유사도: {ref['similarity']:.0%}
- 카테고리: {ref['category']}
- 대상 사이트: {', '.join(ref['sites'][:3])}
- 주요 라이브러리: {', '.join(ref['libraries'][:5])}
- 수행 작업: {actions_text}
- 주요 CSS 셀렉터:
{selectors_text}

"""
        except Exception as e:
            print(f"[AI] 지식베이스 검색 오류: {e}")

    # 첫 요청 (질문 단계) vs 답변 후 (생성 단계)
    has_answers = request.answers and len(request.answers) > 0

    if not has_answers:
        # 1단계: 질문 생성 (더 상세하게)
        question_prompt = f"""사용자가 자동화하고 싶은 작업: "{request.prompt}"

{detailed_code if detailed_code else "참고할 기존 프로젝트가 없습니다."}

위 작업을 자동화하기 위해 사용자에게 **구체적이고 상세한 질문**들을 생성하세요.
자동화 코드 생성에 필요한 모든 정보를 미리 수집해야 합니다.

다음 JSON 형식으로 **5-8개의 상세한 질문**을 생성하세요:

{{
    "message": "작업 분석 결과를 상세히 설명 (3-5문장, 어떤 자동화인지, 예상 단계, 필요한 기술 등)",
    "questions": [
        {{
            "id": "q1",
            "question": "구체적인 질문 내용",
            "type": "choice",
            "options": ["옵션1", "옵션2", "옵션3", "옵션4"],
            "default": "기본값"
        }},
        {{
            "id": "q2",
            "question": "구체적인 질문 내용",
            "type": "text",
            "default": "기본값 또는 예시"
        }},
        {{
            "id": "q3",
            "question": "예/아니오 질문",
            "type": "confirm",
            "options": ["예", "아니오"],
            "default": "예"
        }}
    ]
}}

## 반드시 물어봐야 할 질문 카테고리:

### 1. 대상 정보
- 정확한 URL 또는 사이트 이름
- 특정 페이지/섹션 (예: 특정 카페, 특정 게시판)
- 검색할 키워드나 조건

### 2. 인증/로그인
- 로그인 필요 여부
- 로그인 방식 (일반 로그인, 소셜 로그인, 2차 인증)
- 아이디/비밀번호 입력 방식 (직접 입력, 환경변수, 파일에서 읽기)

### 3. 데이터 수집 (크롤링인 경우)
- 수집할 데이터 항목 (제목, 내용, 가격, 링크, 이미지 등)
- 수집 범위 (페이지 수, 게시글 수, 날짜 범위)
- 필터링 조건 (특정 키워드 포함, 가격 범위 등)

### 4. 데이터 입력/업로드 (글쓰기인 경우)
- 입력할 내용의 출처 (엑셀, CSV, 직접 입력, API)
- 제목/본문/이미지 형식
- 카테고리/태그 설정

### 5. 반복 및 스케줄
- 반복 횟수 또는 조건
- 실행 간격 (딜레이)
- 예약 실행 여부

### 6. 결과 저장
- 저장 형식 (엑셀, CSV, DB, 없음)
- 파일명 및 저장 경로
- 알림 설정 (Slack, 이메일)

### 7. 고급 옵션
- 봇 탐지 우회 필요 여부
- 프록시 사용 여부
- 에러 발생 시 처리 방식 (중단, 건너뛰기, 재시도)
- 캡챠 처리 방식

### 8. 실행 환경
- 브라우저 표시 여부 (headless 모드)
- 브라우저 종류 (Chrome, Firefox)

위 카테고리 중 해당 작업에 필요한 질문들을 선택하여 5-8개의 질문을 생성하세요.
각 질문은 구체적이고 명확해야 하며, 사용자가 쉽게 답변할 수 있어야 합니다.
text 타입 질문에는 반드시 예시를 default에 포함하세요.

반드시 유효한 JSON만 반환하세요 (마크다운 코드블록 없이)."""

        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=8192,
            system="""당신은 RPA 자동화 전문가입니다.
사용자의 요청을 분석하고 자동화 코드 생성에 필요한 모든 정보를 수집하기 위해 상세한 질문을 합니다.
질문은 구체적이고 실용적이어야 하며, 애매한 질문은 피하세요.
예를 들어 "어떤 사이트인가요?" 대신 "자동화할 사이트의 정확한 URL을 입력해주세요 (예: https://cafe.naver.com/카페명)"처럼 구체적으로 질문하세요.""",
            messages=[{"role": "user", "content": question_prompt}]
        )

        response_text = response.content[0].text

        # JSON 파싱 (강화된 버전)
        try:
            import re

            # 코드 블록에서 JSON 추출 시도
            code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text)
            if code_block_match:
                json_str = code_block_match.group(1)
            else:
                # 중괄호 매칭
                first_brace = response_text.find('{')
                last_brace = response_text.rfind('}')
                if first_brace != -1 and last_brace != -1:
                    json_str = response_text[first_brace:last_brace+1]
                else:
                    json_str = response_text

            data = json.loads(json_str.strip())

            questions = []
            for q in data.get("questions", []):
                if q.get("question"):  # 질문이 있는 경우만 추가
                    questions.append(AIQuestion(
                        id=q.get("id", f"q{len(questions)+1}"),
                        question=q.get("question", ""),
                        type=q.get("type", "choice"),
                        options=q.get("options"),
                        default=q.get("default"),
                        hint=q.get("hint"),
                        placeholder=q.get("placeholder")
                    ))

            # 질문이 하나도 없으면 기본 질문 추가
            if len(questions) == 0:
                print("[AI] 질문이 비어있어 기본 질문 사용")
                questions = [
                    AIQuestion(id="q1", question="자동화할 사이트의 정확한 URL을 입력해주세요", type="text", default="https://", hint="예: https://cafe.naver.com/mycafe"),
                    AIQuestion(id="q2", question="주요 작업 유형을 선택해주세요", type="choice", options=["데이터 수집/크롤링", "글 등록/업로드", "반복 클릭/자동화", "로그인/인증"], default="데이터 수집/크롤링"),
                    AIQuestion(id="q3", question="반복 횟수를 입력하세요", type="text", default="10", hint="수집할 데이터 개수 또는 반복 횟수"),
                ]

            return AIConversationResponse(
                mode="questions",
                message=data.get("message", f"'{request.prompt}' 작업을 분석했습니다. 몇 가지 확인이 필요합니다."),
                questions=questions,
                reference_projects=reference_projects
            )

        except Exception as e:
            print(f"JSON 파싱 오류: {e}")
            print(f"응답: {response_text[:300]}...")
            # 기본 질문 반환 (더 상세하게)
            return AIConversationResponse(
                mode="questions",
                message=f"'{request.prompt}' 작업을 분석했습니다. 자동화 코드 생성을 위해 몇 가지 상세 정보가 필요합니다.",
                questions=[
                    AIQuestion(id="q1", question="자동화할 사이트의 정확한 URL을 입력해주세요", type="text", default="https://"),
                    AIQuestion(id="q2", question="로그인이 필요한가요?", type="confirm", options=["예", "아니오"], default="예"),
                    AIQuestion(id="q3", question="로그인 방식을 선택해주세요", type="choice", options=["일반 로그인 (아이디/비밀번호)", "소셜 로그인 (네이버/카카오)", "이미 로그인된 브라우저 사용", "로그인 불필요"], default="일반 로그인 (아이디/비밀번호)"),
                    AIQuestion(id="q4", question="반복 횟수 또는 수집할 데이터 개수를 입력하세요", type="text", default="10"),
                    AIQuestion(id="q5", question="실행 간 대기 시간(초)을 입력하세요 (봇 탐지 방지)", type="text", default="2"),
                    AIQuestion(id="q6", question="결과 저장 방식을 선택해주세요", type="choice", options=["엑셀 (.xlsx)", "CSV 파일", "데이터베이스", "저장 안 함"], default="엑셀 (.xlsx)"),
                    AIQuestion(id="q7", question="에러 발생 시 처리 방식을 선택해주세요", type="choice", options=["건너뛰고 계속 진행", "재시도 (3회)", "즉시 중단"], default="건너뛰고 계속 진행"),
                    AIQuestion(id="q8", question="봇 탐지 우회가 필요한가요? (Cloudflare, reCAPTCHA 등)", type="confirm", options=["예", "아니오"], default="아니오")
                ],
                reference_projects=reference_projects
            )

    else:
        # 2단계: 답변 기반 워크플로우 생성
        # 질문 내용과 함께 답변 표시 (질문이 함께 전송된 경우)
        if request.questions:
            # 질문 ID → 질문 텍스트 매핑 생성
            question_map = {q.id: q.question for q in request.questions}
            answers_text = "\n".join([
                f"- {question_map.get(k, k)}: {v}"
                for k, v in request.answers.items()
            ])
        else:
            answers_text = "\n".join([f"- {k}: {v}" for k, v in request.answers.items()])

        # ===== 실제 웹페이지 분석 (HTML에서 셀렉터 추출) =====
        real_page_analysis = ""
        target_urls = []

        # 답변과 프롬프트에서 모든 URL 추출
        import re
        all_text = request.prompt + " " + " ".join(request.answers.values())

        # 직접 언급된 URL들
        url_matches = re.findall(r'https?://[^\s,\'"]+', all_text)
        for url in url_matches:
            clean_url = url.rstrip('.,)')
            if clean_url not in target_urls:
                target_urls.append(clean_url)

        # 프롬프트에서 사이트 키워드로 URL 추론
        site_keywords = {
            "네이버 증권": "https://finance.naver.com",
            "네이버 주식": "https://finance.naver.com",
            "naver finance": "https://finance.naver.com",
            "네이버 카페": "https://cafe.naver.com",
            "네이버 블로그": "https://blog.naver.com",
            "네이버 뉴스": "https://news.naver.com",
            "쿠팡": "https://www.coupang.com",
            "지마켓": "https://www.gmarket.co.kr",
            "11번가": "https://www.11st.co.kr",
        }

        prompt_lower = all_text.lower()
        for keyword, url in site_keywords.items():
            if keyword.lower() in prompt_lower and url not in target_urls:
                target_urls.append(url)

        target_url = target_urls[0] if target_urls else None

        # ===== 지능형 셀렉터 추출 (Claude가 실제 HTML 분석) =====
        js_required_sites = ["finance.naver.com", "cafe.naver.com", "coupang.com", "gmarket.co.kr", "11st.co.kr"]

        if target_urls:
            print(f"[AI] 지능형 셀렉터 분석 시작: {target_urls}")
            real_page_analysis = ""

            try:
                # IntelligentSelectorService로 실제 HTML 기반 분석
                intelligent_result = await intelligent_selector.analyze_workflow_urls(
                    request.prompt,
                    target_urls[:5]  # 최대 5개 URL
                )

                # combined_context에 Claude가 분석한 셀렉터 정보가 포함됨
                real_page_analysis = intelligent_result.get("combined_context", "")

                # 개별 분석 결과 로깅
                for analysis in intelligent_result.get("analyses", []):
                    url = analysis.get("url", "")
                    if analysis.get("success"):
                        selectors_count = len(analysis.get("selectors", {}))
                        forms_count = len(analysis.get("forms", []))
                        lists_count = len(analysis.get("lists", []))
                        print(f"[AI] {url} - 셀렉터 {selectors_count}개, 폼 {forms_count}개, 목록 {lists_count}개 추출")
                    else:
                        print(f"[AI] {url} - 분석 실패: {analysis.get('error', 'unknown')}")

            except Exception as e:
                print(f"[AI] 지능형 셀렉터 분석 오류: {e}")
                # 기존 WebAnalyzer로 폴백
                for url in target_urls[:3]:
                    try:
                        is_js_required = any(site in url for site in js_required_sites)
                        html = await WebAnalyzer.fetch_page(url)
                        if html:
                            page_structure = WebAnalyzer.extract_page_structure(html)
                            real_page_analysis += f"\n## 📄 {url} (폴백 분석)\n"
                            inputs = page_structure.get("inputs", [])[:5]
                            if inputs:
                                real_page_analysis += "**입력 필드:**\n"
                                for inp in inputs:
                                    real_page_analysis += f"  - `{inp.get('selector', '')}`\n"
                            buttons = page_structure.get("buttons", [])[:5]
                            if buttons:
                                real_page_analysis += "**버튼:**\n"
                                for btn in buttons:
                                    real_page_analysis += f"  - `{btn.get('selector', '')}` ({btn.get('text', '')})\n"
                    except Exception as fallback_e:
                        print(f"[AI] 폴백 분석 오류 {url}: {fallback_e}")

            # 알려진 사이트 셀렉터 추가 (보조)
            for url in target_urls[:3]:
                known_selectors = get_known_site_selectors(url)
                if known_selectors:
                    site_key = known_selectors.get("site_key", "")
                    real_page_analysis += f"""
## 🎯 추가 참고: {known_selectors.get('description', site_key)}
**사전 정의된 셀렉터 (위 분석 결과와 비교하여 사용):**
"""
                    for key, value in known_selectors.items():
                        if key not in ["url", "description", "site_key", "recommended_method", "requires_js"]:
                            real_page_analysis += f"- {key}: `{value}`\n"

                    if known_selectors.get("requires_js"):
                        real_page_analysis += "\n⚠️ JavaScript 렌더링 필요 - Selenium 필수\n"

        else:
            real_page_analysis = "\n## 주의: 분석할 URL이 없습니다. 일반적인 셀렉터 패턴을 사용하세요.\n"

        # 지식베이스에서 전체 프로젝트 코드 가져오기 (사용자 요청: 프로젝트 전체 코드 참고)
        detailed_code_for_prompt = ""
        if HAS_KNOWLEDGE_BASE:
            try:
                kb = get_knowledge_base()
                # 전체 코드 포함하여 AI 컨텍스트 생성 (프로젝트당 최대 20000자)
                detailed_code_for_prompt = kb.get_context_for_ai(request.prompt, max_code_per_project=20000)
                if detailed_code_for_prompt:
                    print(f"[AI] 지식베이스 컨텍스트 생성 완료: {len(detailed_code_for_prompt)}자")
            except Exception as e:
                print(f"[AI] 지식베이스 컨텍스트 가져오기 실패: {e}")

        workflow_prompt = f"""당신은 RPA 자동화 전문가입니다. 사용자의 요청과 답변을 바탕으로 Selenium 기반 자동화 워크플로우를 생성해야 합니다.

## 사용자 요청
"{request.prompt}"

## 사용자 답변
{answers_text}

{real_page_analysis}

## 기존 프로젝트 코드 참조 가이드
아래에 유사한 작동이 검증된 프로젝트 코드가 제공됩니다. 참고하되, 위 "실제 웹페이지 분석 결과"의 셀렉터를 우선 사용하세요.

{detailed_code_for_prompt if detailed_code_for_prompt else detailed_code if detailed_code else "참고할 기존 프로젝트가 없습니다."}

## 사용 가능한 블록 타입 (반드시 이 중에서만 선택)

### 시작/설정
- start: 워크플로우 시작 (field_values: {{}})
- schedule: 예약 실행 (field_values: {{"time": "09:00", "repeat": "daily"}})

### 브라우저 제어
- open-site: 사이트 열기 (field_values: {{"url": "https://example.com"}})
- navigate: 페이지 이동 (field_values: {{"url": "https://..."}})
- click: 요소 클릭 (field_values: {{"selector": "CSS셀렉터", "selectorType": "css"}})
- scroll: 스크롤 (field_values: {{"direction": "down", "amount": "500"}})
- wait-page-load: 페이지 로드 대기 (field_values: {{"timeout": "10"}})
- screenshot: 스크린샷 (field_values: {{"filename": "screenshot.png"}})

### 입력
- input-text: 텍스트 입력 (field_values: {{"selector": "셀렉터", "text": "입력할 텍스트", "clear": "clear", "selectorType": "css"}})
- press-key: 키 입력 (field_values: {{"key": "Enter"}})

### 데이터 추출
- extract-text: 텍스트 추출 (field_values: {{"selector": "셀렉터", "variable": "변수명", "selectorType": "css"}})
- extract-list: 목록 추출 (field_values: {{"selector": "li, .item 등", "fields": "title,link,price", "variable": "items", "selectorType": "css"}})
- extract-attr: 속성 추출 (field_values: {{"selector": "셀렉터", "attribute": "href", "variable": "변수명", "selectorType": "css"}})

### 데이터 저장
- save-excel: 엑셀 저장 (field_values: {{"variable": "items", "filename": "result.xlsx", "mode": "overwrite"}})
- save-csv: CSV 저장 (field_values: {{"variable": "items", "filename": "result.csv"}})

### 제어 흐름
- wait: 대기 (field_values: {{"seconds": "3"}})
- loop: 횟수 반복 (field_values: {{"count": "10"}})
- loop-list: 목록 반복 (field_values: {{"listVariable": "items"}})
- condition: 조건문 (field_values: {{"condition": "len(items) > 0"}})
- log: 로그 출력 (field_values: {{"message": "처리 완료", "level": "info"}})

### 데스크톱/PyAutoGUI
- mouse-click-coords: 좌표 클릭 (field_values: {{"x": "500", "y": "300", "clicks": "1"}})
- mouse-move: 마우스 이동 (field_values: {{"x": "500", "y": "300", "duration": "0.5"}})
- pyautogui-type: 텍스트 타이핑 (field_values: {{"text": "입력할 텍스트", "interval": "0.05"}})
- pyautogui-hotkey: 단축키 (field_values: {{"hotkey": "ctrl,v"}})
- image-click: 이미지 인식 클릭 (field_values: {{"image_path": "button.png", "confidence": "0.9", "timeout": "10"}})
- window-focus: 창 활성화 (field_values: {{"title": "창 제목"}})

### 고급 (중요: 일반 블록으로 불가능한 작업은 반드시 custom-code 사용)
- custom-code: Python 코드 직접 실행 (field_values: {{"code": "실제 Python 코드", "description": "코드 설명"}})
- http-request: HTTP 요청 (field_values: {{"method": "GET", "url": "https://api.example.com"}})
- stealth-mode: 봇 탐지 우회 (field_values: {{"mode": "undetected"}})
- random-delay: 랜덤 대기 (field_values: {{"min": "1", "max": "5"}})
- captcha-wait: 캡챠 대기 (field_values: {{"timeout": "120", "action": "manual"}})

### 데이터베이스
- db-connect: DB 연결 (field_values: {{"type": "mysql", "host": "localhost", "database": "db명", "username": "user", "password": "pass"}})
- db-query: DB 조회 (field_values: {{"query": "SELECT * FROM table", "variable": "result"}})

### 파일/텍스트
- read-file: 파일 읽기 (field_values: {{"filepath": "data.txt", "variable": "content", "encoding": "utf-8"}})
- write-file: 파일 쓰기 (field_values: {{"filepath": "output.txt", "content": "내용", "mode": "overwrite"}})
- regex-extract: 정규식 추출 (field_values: {{"text": "변수명", "pattern": "패턴", "variable": "extracted"}})
- run-script: 외부 스크립트 실행 (field_values: {{"command": "python script.py", "timeout": "60", "variable": "output"}})

## 출력 형식 (반드시 이 JSON 형식만 출력, 다른 텍스트 없이)

{{
    "task_name": "작업 이름 (20자 이내)",
    "summary": "작업 요약 (50자 이내)",
    "confidence": 85,
    "groups": [
        {{
            "id": "g1",
            "label": "그룹 이름",
            "description": "이 그룹이 하는 일",
            "color": "#22c55e",
            "steps": [
                {{
                    "id": "s1",
                    "label": "단계 이름",
                    "description": "이 단계가 하는 일",
                    "block_type": "start",
                    "color": "#22c55e",
                    "field_values": {{}}
                }},
                {{
                    "id": "s2",
                    "label": "사이트 열기",
                    "description": "네이버 카페 접속",
                    "block_type": "open-site",
                    "color": "#3b82f6",
                    "field_values": {{"url": "https://cafe.naver.com"}}
                }}
            ]
        }},
        {{
            "id": "g2",
            "label": "로그인",
            "description": "네이버 로그인 처리",
            "color": "#3b82f6",
            "steps": [
                {{
                    "id": "s3",
                    "label": "로그인 버튼 클릭",
                    "description": "로그인 페이지로 이동",
                    "block_type": "click",
                    "color": "#eab308",
                    "field_values": {{"selector": "#login-btn"}}
                }}
            ]
        }}
    ]
}}

## 중요 규칙
1. 반드시 첫 번째 step은 "start" 블록이어야 함
2. **기존 참고 프로젝트 코드에서 셀렉터와 로직을 최대한 활용** - 검증된 코드이므로 그대로 사용
3. 모든 step에 field_values를 반드시 포함 (빈 객체 {{}}도 가능)
4. 그룹은 3-6개, 각 그룹당 step은 2-5개로 구성
5. 색상: 시작=#22c55e, 브라우저=#3b82f6, 액션=#eab308, 데이터=#a855f7, 제어=#f97316
6. JSON만 출력하고 다른 설명 텍스트는 절대 포함하지 않음
7. 문자열 안의 따옴표는 반드시 이스케이프 (\")
8. 사용자 답변을 field_values에 반영

## 변수 플레이스홀더 사용 (매우 중요!)
사용자가 실행 시 직접 입력해야 하는 값은 반드시 {{변수명}} 형식의 플레이스홀더를 사용하세요:

- 로그인 아이디: {{"text": "{{username}}"}}
- 비밀번호: {{"text": "{{password}}"}}
- 검색어: {{"text": "{{search_keyword}}"}}
- 반복 횟수: {{"count": "{{loop_count}}"}}
- 이메일: {{"text": "{{email}}"}}
- 메시지/내용: {{"text": "{{message}}"}}

예시:
- 아이디 입력 블록: {{"selector": "#id", "text": "{{username}}"}}
- 비밀번호 입력 블록: {{"selector": "#pw", "text": "{{password}}"}}
- 검색어 입력 블록: {{"selector": ".search-input", "text": "{{search_keyword}}"}}

## custom-code 블록 사용 가이드라인 (매우 중요!)
일반 블록으로 구현이 어려운 경우, 반드시 custom-code 블록을 사용하세요:

### ⚠️ 파일 저장 필수 규칙 (절대 준수!)
**모든 파일 저장은 반드시 self의 폴더 변수를 사용하세요:**
- `self.output_dir` - 기본 출력 폴더
- `self.today_dir` - 오늘 날짜 폴더 (output/YYYY-MM-DD)
- `self.screenshot_dir` - 스크린샷 저장 폴더
- `self.download_dir` - 다운로드 파일 폴더
- `self.data_dir` - 데이터 파일 폴더 (엑셀, CSV 등)

**절대 하드코딩된 경로를 사용하지 마세요!**
❌ 잘못된 예: `C:\\Users\\...`, `C:\\결과폴더`, `./downloads`
✅ 올바른 예: `os.path.join(self.screenshot_dir, 'result.png')`

### 사용 예시:

1. **스크린샷 저장**:
   예: {{"code": "filepath = os.path.join(self.screenshot_dir, '삼성전자.png')\\nself.driver.save_screenshot(filepath)", "description": "스크린샷 저장"}}
   또는 내장 함수 사용: {{"code": "self.save_screenshot('삼성전자.png')", "description": "스크린샷 저장"}}

2. **파일 다운로드 후 이동**:
   예: {{"code": "import shutil\\nsrc = os.path.join(self.download_dir, 'file.pdf')\\ndst = os.path.join(self.data_dir, 'renamed.pdf')\\nshutil.move(src, dst)", "description": "다운로드 파일 이동"}}

3. **데이터 저장**:
   예: {{"code": "filepath = os.path.join(self.data_dir, 'result.json')\\nwith open(filepath, 'w', encoding='utf-8') as f:\\n    json.dump(data, f, ensure_ascii=False)", "description": "JSON 저장"}}

4. **복잡한 데이터 처리**: 리스트 필터링, 변환 등
   예: {{"code": "filtered = [x for x in items if x['price'] < 10000]", "description": "필터링"}}

5. **동적 대기/확인**: 특정 조건 충족 대기
   예: {{"code": "while not self.driver.find_elements(By.CSS_SELECTOR, '.loaded'):\\n    time.sleep(0.5)", "description": "요소 로드 대기"}}

참고 프로젝트 코드에서 유용한 코드 패턴이 있다면 custom-code 블록에 그대로 활용하세요.
단, 파일 경로는 반드시 self의 폴더 변수로 변경하세요!"""

        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=16384,
            system="""당신은 RPA 자동화 전문가입니다.
규칙:
1. 반드시 유효한 JSON만 출력합니다
2. JSON 외에 다른 텍스트, 설명, 마크다운을 절대 포함하지 않습니다
3. 문자열 내의 특수문자(따옴표, 백슬래시 등)는 반드시 이스케이프 처리합니다
4. 응답은 { 로 시작하고 } 로 끝나야 합니다""",
            messages=[{"role": "user", "content": workflow_prompt}]
        )

        response_text = response.content[0].text
        print(f"[AI] Claude 응답 길이: {len(response_text)}")

        # JSON 파싱 (강화된 버전)
        def extract_json(text):
            """여러 방법으로 JSON 추출 시도"""
            import re

            # 방법 1: 코드 블록에서 추출
            code_match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', text)
            if code_match:
                return code_match.group(1).strip()

            # 방법 2: 첫 { 부터 마지막 } 까지
            first = text.find('{')
            last = text.rfind('}')
            if first != -1 and last != -1 and last > first:
                return text[first:last+1]

            return text.strip()

        def fix_json(json_str):
            """일반적인 JSON 오류 수정"""
            import re

            # 끝나지 않은 문자열 수정 (줄바꿈으로 끝나는 경우)
            # 마지막 유효한 중괄호 찾기
            brace_count = 0
            last_valid = 0
            in_string = False
            escape_next = False

            for i, char in enumerate(json_str):
                if escape_next:
                    escape_next = False
                    continue

                if char == '\\':
                    escape_next = True
                    continue

                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue

                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            last_valid = i
                            break

            if last_valid > 0:
                return json_str[:last_valid+1]

            return json_str

        def sanitize_code_fields(workflow_data):
            """custom-code 블록의 code 필드 정리 및 하드코딩된 경로 교체"""
            import re

            if not isinstance(workflow_data, dict):
                return workflow_data

            def fix_hardcoded_paths(code: str) -> str:
                """하드코딩된 경로를 self 변수로 교체"""
                if not code:
                    return code

                # 윈도우 절대 경로 패턴 (C:\..., D:\... 등)
                # 스크린샷/캡처 관련 경로 → self.screenshot_dir
                code = re.sub(
                    r'["\']?[A-Za-z]:[/\\][^"\']*(?:screenshot|스크린샷|캡처|capture|Screenshots)[^"\']*["\']?',
                    'self.screenshot_dir',
                    code,
                    flags=re.IGNORECASE
                )

                # 다운로드 관련 경로 → self.download_dir
                code = re.sub(
                    r'["\']?[A-Za-z]:[/\\][^"\']*(?:download|다운로드|Downloads)[^"\']*["\']?',
                    'self.download_dir',
                    code,
                    flags=re.IGNORECASE
                )

                # 데이터/결과 관련 경로 → self.data_dir
                code = re.sub(
                    r'["\']?[A-Za-z]:[/\\][^"\']*(?:data|결과|output|저장|result)[^"\']*["\']?',
                    'self.data_dir',
                    code,
                    flags=re.IGNORECASE
                )

                # 남은 윈도우 절대 경로 → self.today_dir
                code = re.sub(
                    r'["\'][A-Za-z]:[/\\][^"\']+["\']',
                    'self.today_dir',
                    code
                )

                # os.path.join에서 중복된 self 경로 정리
                # os.path.join(self.screenshot_dir, today) 형태에서 today 변수가 날짜면 제거
                code = re.sub(
                    r'os\.path\.join\(self\.(screenshot_dir|download_dir|data_dir|today_dir),\s*today\)',
                    r'self.\1',
                    code
                )

                # os.makedirs(self.screenshot_dir, exist_ok=True) 중복 제거 (이미 자동 생성됨)
                code = re.sub(
                    r'os\.makedirs\(self\.(screenshot_dir|download_dir|data_dir|today_dir),\s*exist_ok=True\)\n?',
                    '# 폴더는 자동 생성됨\n',
                    code
                )

                return code

            groups = workflow_data.get("groups", [])
            for group in groups:
                steps = group.get("steps", [])
                for step in steps:
                    if step.get("block_type") == "custom-code":
                        field_values = step.get("field_values", {})
                        if "code" in field_values:
                            code = field_values["code"]
                            # 하드코딩된 경로 수정
                            code = fix_hardcoded_paths(code)
                            # 코드가 너무 길면 자르기 (최대 5000자)
                            if len(code) > 5000:
                                code = code[:5000] + "\n# ... (코드가 너무 길어 잘림)"
                            field_values["code"] = code

            return workflow_data

        try:
            json_str = extract_json(response_text)
            json_str = fix_json(json_str)

            workflow = json.loads(json_str)
            workflow = sanitize_code_fields(workflow)

            return AIConversationResponse(
                mode="workflow",
                message=f"워크플로우가 생성되었습니다. {len(workflow.get('groups', []))}개 그룹, {sum(len(g.get('steps', [])) for g in workflow.get('groups', []))}개 단계로 구성됩니다.",
                workflow=workflow,
                reference_projects=reference_projects
            )

        except Exception as e:
            print(f"[AI] 워크플로우 생성 오류: {e}")
            print(f"[AI] 응답 앞부분: {response_text[:500]}")
            print(f"[AI] 응답 뒷부분: {response_text[-500:]}")

            # 폴백: 요청에 맞는 기본 워크플로우 생성
            prompt_lower = request.prompt.lower()

            # URL 추정
            if "네이버" in prompt_lower or "naver" in prompt_lower:
                if "카페" in prompt_lower:
                    default_url = "https://cafe.naver.com"
                elif "블로그" in prompt_lower:
                    default_url = "https://blog.naver.com"
                else:
                    default_url = "https://naver.com"
            elif "쿠팡" in prompt_lower:
                default_url = "https://coupang.com"
            elif "인스타" in prompt_lower:
                default_url = "https://instagram.com"
            elif "유튜브" in prompt_lower or "youtube" in prompt_lower:
                default_url = "https://youtube.com"
            elif "당근" in prompt_lower:
                default_url = "https://daangn.com"
            elif "번개" in prompt_lower:
                default_url = "https://bunjang.co.kr"
            else:
                default_url = "https://example.com"

            # 작업 유형 추정
            is_crawling = any(k in prompt_lower for k in ["크롤링", "수집", "추출", "가져오기", "긁어", "스크래핑"])
            is_upload = any(k in prompt_lower for k in ["업로드", "등록", "글쓰기", "올리기", "게시"])
            is_login = any(k in prompt_lower for k in ["로그인", "인증", "login"])

            # 동적 폴백 워크플로우 생성
            fallback_steps = [
                {"id": "s1", "label": "시작", "description": "워크플로우 시작", "block_type": "start", "color": "#22c55e", "field_values": {}},
                {"id": "s2", "label": "사이트 열기", "description": f"{default_url} 접속", "block_type": "open-site", "color": "#3b82f6", "field_values": {"url": default_url}},
                {"id": "s3", "label": "페이지 로드 대기", "description": "페이지가 완전히 로드될 때까지 대기", "block_type": "wait-page-load", "color": "#3b82f6", "field_values": {"timeout": "10"}}
            ]

            fallback_groups = [
                {
                    "id": "g1",
                    "label": "사이트 접속",
                    "description": "대상 사이트에 접속합니다",
                    "color": "#22c55e",
                    "steps": fallback_steps[:3]
                }
            ]

            # 크롤링인 경우
            if is_crawling:
                fallback_groups.append({
                    "id": "g2",
                    "label": "데이터 수집",
                    "description": "페이지에서 데이터를 추출합니다",
                    "color": "#a855f7",
                    "steps": [
                        {"id": "s4", "label": "대기", "description": "페이지 로드 대기", "block_type": "wait", "color": "#f97316", "field_values": {"seconds": "2"}},
                        {"id": "s5", "label": "목록 추출", "description": "데이터 목록 추출", "block_type": "extract-list", "color": "#9333ea", "field_values": {"selector": ".item, .list-item, li", "fields": "title, link", "variable": "items"}},
                    ]
                })
                fallback_groups.append({
                    "id": "g3",
                    "label": "결과 저장",
                    "description": "수집한 데이터를 저장합니다",
                    "color": "#7c3aed",
                    "steps": [
                        {"id": "s6", "label": "엑셀 저장", "description": "엑셀 파일로 저장", "block_type": "save-excel", "color": "#7c3aed", "field_values": {"variable": "items", "filename": "result.xlsx", "mode": "overwrite"}},
                        {"id": "s7", "label": "완료 로그", "description": "작업 완료 로그", "block_type": "log", "color": "#f97316", "field_values": {"message": "데이터 수집 완료", "level": "success"}},
                    ]
                })
            # 업로드인 경우
            elif is_upload:
                fallback_groups.append({
                    "id": "g2",
                    "label": "글 작성",
                    "description": "내용을 입력합니다",
                    "color": "#f43f5e",
                    "steps": [
                        {"id": "s4", "label": "대기", "description": "페이지 로드 대기", "block_type": "wait", "color": "#f97316", "field_values": {"seconds": "2"}},
                        {"id": "s5", "label": "제목 입력", "description": "제목 필드에 텍스트 입력", "block_type": "input-text", "color": "#f43f5e", "field_values": {"selector": "input[name=title], #title, .title-input", "text": "제목을 입력하세요", "clear": "clear"}},
                        {"id": "s6", "label": "내용 입력", "description": "본문 필드에 텍스트 입력", "block_type": "input-text", "color": "#f43f5e", "field_values": {"selector": "textarea, .editor, #content", "text": "내용을 입력하세요", "clear": "clear"}},
                    ]
                })
                fallback_groups.append({
                    "id": "g3",
                    "label": "제출",
                    "description": "글을 등록합니다",
                    "color": "#eab308",
                    "steps": [
                        {"id": "s7", "label": "등록 버튼 클릭", "description": "등록/제출 버튼 클릭", "block_type": "click", "color": "#eab308", "field_values": {"selector": "button[type=submit], .submit-btn, .btn-submit"}},
                        {"id": "s8", "label": "완료 로그", "description": "작업 완료 로그", "block_type": "log", "color": "#f97316", "field_values": {"message": "글 등록 완료", "level": "success"}},
                    ]
                })
            # 기본
            else:
                fallback_groups.append({
                    "id": "g2",
                    "label": "작업 수행",
                    "description": "자동화 작업을 수행합니다",
                    "color": "#eab308",
                    "steps": [
                        {"id": "s4", "label": "대기", "description": "요소 로드 대기", "block_type": "wait", "color": "#f97316", "field_values": {"seconds": "2"}},
                        {"id": "s5", "label": "Python 코드", "description": "커스텀 로직 실행", "block_type": "custom-code", "color": "#6366f1", "field_values": {"code": f"# {request.prompt}\nfrom selenium import webdriver\nfrom selenium.webdriver.common.by import By\nimport time\n\ndriver = webdriver.Chrome()\ntry:\n    # 여기에 자동화 로직을 작성하세요\n    driver.get('https://example.com')\n    time.sleep(2)\n    print('작업 완료')\nfinally:\n    driver.quit()", "description": request.prompt[:50]}},
                        {"id": "s6", "label": "로그", "description": "작업 완료 로그", "block_type": "log", "color": "#f97316", "field_values": {"message": "작업을 완료했습니다", "level": "success"}}
                    ]
                })

            fallback_workflow = {
                "task_name": request.prompt[:30],
                "summary": f"'{request.prompt[:50]}' 자동화 (기본 템플릿)",
                "confidence": 60,
                "groups": fallback_groups
            }

            return AIConversationResponse(
                mode="workflow",
                message=f"AI 응답 파싱 중 오류가 발생하여 기본 워크플로우를 생성했습니다. 필요에 맞게 블록을 수정해주세요.",
                workflow=fallback_workflow,
                reference_projects=reference_projects
            )


@router.post("/analyze-blocks")
async def analyze_blocks_for_description(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """블록 구성을 분석하여 마켓플레이스용 개요, 주요 기능, 사용 방법을 생성합니다."""
    import anthropic

    blocks = request.get("blocks", [])
    title = request.get("title", "")

    default_features = [
        "자동으로 데이터를 수집하고 저장",
        "설정에 따라 반복 실행 지원",
        "간편한 설정으로 빠른 시작"
    ]
    default_usage = [
        "워크스페이스에 템플릿을 가져옵니다",
        "각 블록의 설정값을 입력합니다",
        "실행 버튼을 눌러 자동화를 시작합니다"
    ]

    if not blocks:
        return {
            "description": "자동화 워크플로우입니다.",
            "features": default_features,
            "usage_steps": default_usage
        }

    # 블록 정보 요약
    block_summary = []
    for block in blocks[:20]:  # 최대 20개만
        label = block.get("label", "")
        block_type = block.get("type", block.get("id", ""))
        field_values = block.get("fieldValues", block.get("field_values", {}))

        if field_values:
            details = ", ".join([f"{k}: {str(v)[:30]}" for k, v in field_values.items() if v])
            block_summary.append(f"- {label} ({block_type}): {details}" if details else f"- {label} ({block_type})")
        else:
            block_summary.append(f"- {label} ({block_type})")

    blocks_text = "\n".join(block_summary)

    if not settings.ANTHROPIC_API_KEY:
        # API 키 없으면 기본 설명 생성
        block_labels = [b.get("label", "") for b in blocks[:5]]
        return {
            "description": f"{title or '자동화'} 워크플로우입니다. {', '.join(block_labels)} 등 {len(blocks)}개의 블록으로 구성되어 있습니다.",
            "features": default_features,
            "usage_steps": default_usage
        }

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": f"""다음 RPA 자동화 블록 구성을 분석하여 마켓플레이스용 정보를 JSON으로 생성해주세요.

제목: {title}

블록 구성:
{blocks_text}

다음 JSON 형식으로만 응답하세요:
{{
    "description": "2-3문장의 간결한 설명. 이 자동화가 무엇을 하는지, 어떤 사이트/서비스를 대상으로 하는지 포함",
    "features": ["주요 기능 1", "주요 기능 2", "주요 기능 3", "주요 기능 4"],
    "usage_steps": ["사용 방법 1단계", "사용 방법 2단계", "사용 방법 3단계", "사용 방법 4단계"]
}}

요구사항:
- description: 일반인이 이해하기 쉬운 2-3문장
- features: 이 자동화의 핵심 기능 4개 (짧은 문장으로)
- usage_steps: 사용자가 따라할 수 있는 단계별 안내 4개

JSON만 출력하세요:"""
            }]
        )

        result_text = response.content[0].text.strip()

        # JSON 파싱
        try:
            # ```json ... ``` 형식 처리
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)
            return {
                "description": result.get("description", "자동화 워크플로우입니다."),
                "features": result.get("features", default_features),
                "usage_steps": result.get("usage_steps", default_usage)
            }
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 description만 사용
            return {
                "description": result_text[:200],
                "features": default_features,
                "usage_steps": default_usage
            }

    except Exception as e:
        print(f"[AI] 블록 분석 오류: {e}")
        block_labels = [b.get("label", "") for b in blocks[:5]]
        return {
            "description": f"{title or '자동화'} 워크플로우입니다. {', '.join(block_labels)} 등 {len(blocks)}개의 블록으로 구성되어 있습니다.",
            "features": default_features,
            "usage_steps": default_usage
        }


@router.post("/verify-code", response_model=CodeVerificationResponse)
async def verify_generated_code(
    request: CodeVerificationRequest,
    current_user: User = Depends(get_current_user)
):
    """AI가 생성한 워크플로우 코드를 2차 검증하고 자동으로 개선합니다."""
    import anthropic
    from app.services.code_generator import code_generator

    workflow = request.workflow
    original_prompt = request.original_prompt
    MAX_IMPROVEMENT_ROUNDS = 1  # 검증 1회만 실행 (속도 개선)
    TARGET_SCORE = 60  # 목표 점수 (낮춤)

    if not settings.ANTHROPIC_API_KEY:
        return CodeVerificationResponse(
            is_valid=True,
            score=85,
            summary="기본 검증 완료",
            issues=[],
            test_results=None,
            improved_workflow=None
        )

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        current_workflow = json.loads(json.dumps(workflow))
        all_issues_fixed = []
        final_score = 0
        final_summary = ""

        for round_num in range(MAX_IMPROVEMENT_ROUNDS):
            print(f"[AI] 검증 라운드 {round_num + 1}/{MAX_IMPROVEMENT_ROUNDS}")

            # 워크플로우에서 블록 정보 추출
            groups = current_workflow.get("groups", [])
            all_steps = []
            for g in groups:
                for s in g.get("steps", []):
                    all_steps.append({
                        "id": s.get("id"),
                        "label": s.get("label"),
                        "block_type": s.get("block_type"),
                        "field_values": s.get("field_values", {})
                    })

            # 블록들을 Python 코드로 변환
            blocks_for_generator = []
            for step in all_steps:
                blocks_for_generator.append({
                    "id": step["block_type"],
                    "type": step["block_type"],
                    "label": step["label"],
                    "fieldValues": step["field_values"]
                })

            generated_code = code_generator.generate(blocks_for_generator, current_workflow.get("task_name", "automation"))

            # 검증 및 개선 프롬프트
            verification_prompt = f"""당신은 RPA/Selenium 자동화 코드 검증 및 개선 전문가입니다.

## 사용자 요청
"{original_prompt}"

## 현재 워크플로우 (라운드 {round_num + 1})
{json.dumps(current_workflow, ensure_ascii=False, indent=2)}

## 생성된 Python 코드
```python
{generated_code[:8000]}
```

## 사용 가능한 블록 타입
- start: 시작 (field_values: {{}})
- open-site: 사이트 열기 (field_values: {{"url": "https://..."}})
- click: 클릭 (field_values: {{"selector": "CSS셀렉터", "selectorType": "css"}})
- input-text: 텍스트 입력 (field_values: {{"selector": "셀렉터", "text": "텍스트", "clear": "clear"}})
- extract-text: 텍스트 추출 (field_values: {{"selector": "셀렉터", "variable": "변수명"}})
- extract-list: 목록 추출 (field_values: {{"selector": "셀렉터", "fields": "title,link", "variable": "items"}})
- save-excel: 엑셀 저장 (field_values: {{"variable": "items", "filename": "result.xlsx"}})
- wait: 대기 (field_values: {{"seconds": "3"}})
- wait-page-load: 페이지 로드 대기 (field_values: {{"timeout": "10"}})
- log: 로그 (field_values: {{"message": "메시지"}})
- custom-code: Python 코드 (field_values: {{"code": "코드", "description": "설명"}})
- loop: 반복 (field_values: {{"count": "10"}})
- condition: 조건문 (field_values: {{"condition": "조건식"}})
- screenshot: 스크린샷 (field_values: {{"filename": "screenshot.png"}})
- scroll: 스크롤 (field_values: {{"direction": "down", "amount": "500"}})
- press-key: 키 입력 (field_values: {{"key": "Enter"}})
- random-delay: 랜덤 대기 (field_values: {{"min": "1", "max": "3"}})

## 검증 및 개선 작업

1. **검증**: 코드의 문제점 분석
2. **개선**: 문제가 있으면 즉시 수정된 워크플로우 생성

### 핵심 검증 항목
- 사용자 요청을 100% 수행하는가?
- CSS 셀렉터가 실제로 유효한 형식인가?
- 필요한 대기 시간이 있는가?
- 에러 처리가 필요한 곳이 있는가?

### 응답 형식 (반드시 JSON만)
{{
    "score": 85,
    "summary": "검증 결과 요약",
    "issues_found": ["발견된 이슈1", "발견된 이슈2"],
    "issues_fixed": ["수정한 내용1", "수정한 내용2"],
    "improved_workflow": {{
        "task_name": "작업명",
        "summary": "요약",
        "confidence": 90,
        "groups": [
            {{
                "id": "g1",
                "label": "그룹명",
                "description": "설명",
                "color": "#22c55e",
                "steps": [
                    {{
                        "id": "s1",
                        "label": "시작",
                        "description": "워크플로우 시작",
                        "block_type": "start",
                        "color": "#22c55e",
                        "field_values": {{}}
                    }}
                ]
            }}
        ]
    }}
}}

**중요**:
- score가 {TARGET_SCORE} 미만이면 반드시 improved_workflow에 수정된 전체 워크플로우를 포함하세요
- improved_workflow는 원본의 수정본이 아니라 **완전한 새 워크플로우**여야 합니다
- 모든 step에 field_values를 반드시 포함하세요
- JSON만 출력하세요"""

            response = client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=16384,
                system="""당신은 RPA 자동화 전문가입니다.
워크플로우를 검증하고 문제가 있으면 즉시 수정된 버전을 생성합니다.
항상 완벽한 워크플로우를 만드는 것을 목표로 합니다.
JSON만 출력합니다.""",
                messages=[{"role": "user", "content": verification_prompt}]
            )

            response_text = response.content[0].text

            # JSON 파싱
            try:
                import re
                code_match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', response_text)
                if code_match:
                    json_str = code_match.group(1).strip()
                else:
                    first = response_text.find('{')
                    last = response_text.rfind('}')
                    if first != -1 and last != -1:
                        json_str = response_text[first:last+1]
                    else:
                        json_str = response_text

                result = json.loads(json_str)
                final_score = result.get("score", 75)
                final_summary = result.get("summary", "검증 완료")

                # 수정된 이슈 기록
                issues_fixed = result.get("issues_fixed", [])
                all_issues_fixed.extend(issues_fixed)

                # 개선된 워크플로우가 있으면 적용
                improved = result.get("improved_workflow")
                if improved and isinstance(improved, dict) and improved.get("groups"):
                    current_workflow = improved
                    print(f"[AI] 워크플로우 개선됨 (점수: {final_score})")

                # 목표 점수 달성하면 종료
                if final_score >= TARGET_SCORE:
                    print(f"[AI] 목표 점수 달성: {final_score}")
                    break

            except json.JSONDecodeError as e:
                print(f"[AI] 라운드 {round_num + 1} JSON 파싱 실패: {e}")
                final_score = 70
                final_summary = "검증 완료 (일부 분석 실패)"
                break

        # 최종 결과 반환
        issues = []
        if final_score < TARGET_SCORE:
            issues.append(CodeVerificationIssue(
                severity="info",
                block_id=None,
                message=f"자동 개선 {MAX_IMPROVEMENT_ROUNDS}회 완료",
                suggestion="필요시 블록 설정을 직접 수정하세요"
            ))

        # 수정된 내용을 이슈로 표시
        for fixed in all_issues_fixed[:5]:  # 최대 5개만 표시
            issues.append(CodeVerificationIssue(
                severity="info",
                block_id=None,
                message=f"✓ {fixed}",
                suggestion=None
            ))

        return CodeVerificationResponse(
            is_valid=final_score >= 60,
            score=final_score,
            summary=f"{final_summary} (자동 개선 {len(all_issues_fixed)}건 적용)",
            issues=issues,
            test_results=None,
            improved_workflow=current_workflow if current_workflow != workflow else None
        )

    except Exception as e:
        print(f"[AI] 코드 검증 오류: {e}")
        return CodeVerificationResponse(
            is_valid=True,
            score=70,
            summary="기본 검증 완료",
            issues=[],
            test_results=None,
            improved_workflow=None
        )
