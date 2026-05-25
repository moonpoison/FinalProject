"""
셀렉터 검증 서비스
실제 웹페이지에서 CSS/XPath 셀렉터가 존재하는지 검증하고,
더 나은 셀렉터를 추천합니다.
"""

import asyncio
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from lxml import html as lxml_html
import cssselect


@dataclass
class SelectorValidation:
    """셀렉터 검증 결과"""
    selector: str
    selector_type: str  # "css" or "xpath"
    is_valid: bool
    match_count: int
    sample_text: Optional[str] = None
    sample_html: Optional[str] = None
    error: Optional[str] = None
    alternatives: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0.0 ~ 1.0


@dataclass
class PageAnalysis:
    """페이지 분석 결과"""
    url: str
    title: str
    html_length: int
    fetch_success: bool
    error: Optional[str] = None
    forms: List[Dict] = field(default_factory=list)
    inputs: List[Dict] = field(default_factory=list)
    buttons: List[Dict] = field(default_factory=list)
    lists: List[Dict] = field(default_factory=list)
    links: List[Dict] = field(default_factory=list)


class SelectorValidator:
    """셀렉터 검증 및 추천 서비스"""

    # 일반적인 User-Agent
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # 요청 타임아웃
    TIMEOUT = 15.0

    # 동적 사이트 (JavaScript 렌더링 필요)
    JS_REQUIRED_SITES = [
        "coupang.com", "gmarket.co.kr", "11st.co.kr",
        "instagram.com", "twitter.com", "facebook.com",
        "naver.com/search", "google.com/search"
    ]

    def __init__(self):
        self._html_cache: Dict[str, Tuple[str, float]] = {}
        self._cache_ttl = 300  # 5분 캐시

    async def fetch_html(self, url: str, use_cache: bool = True) -> Tuple[Optional[str], Optional[str]]:
        """
        URL에서 HTML을 가져옵니다.

        Returns:
            (html_content, error_message)
        """
        import time

        # 캐시 확인
        if use_cache and url in self._html_cache:
            cached_html, cached_time = self._html_cache[url]
            if time.time() - cached_time < self._cache_ttl:
                return cached_html, None

        try:
            headers = {
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            async with httpx.AsyncClient(
                timeout=self.TIMEOUT,
                follow_redirects=True,
                verify=False  # SSL 검증 비활성화 (일부 사이트 호환성)
            ) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                # 인코딩 처리
                content_type = response.headers.get("content-type", "")
                if "charset=" in content_type:
                    encoding = content_type.split("charset=")[-1].split(";")[0].strip()
                else:
                    encoding = response.encoding or "utf-8"

                try:
                    html = response.content.decode(encoding)
                except:
                    html = response.content.decode("utf-8", errors="ignore")

                # 캐시 저장
                self._html_cache[url] = (html, time.time())

                return html, None

        except httpx.TimeoutException:
            return None, f"타임아웃: {url} 응답 없음 ({self.TIMEOUT}초)"
        except httpx.HTTPStatusError as e:
            return None, f"HTTP 오류: {e.response.status_code}"
        except Exception as e:
            return None, f"요청 실패: {str(e)}"

    def _is_js_required(self, url: str) -> bool:
        """JavaScript 렌더링이 필요한 사이트인지 확인"""
        for site in self.JS_REQUIRED_SITES:
            if site in url:
                return True
        return False

    def validate_css_selector(self, html: str, selector: str) -> SelectorValidation:
        """CSS 셀렉터 검증"""
        try:
            soup = BeautifulSoup(html, "lxml")
            elements = soup.select(selector)

            match_count = len(elements)
            is_valid = match_count > 0

            sample_text = None
            sample_html = None

            if elements:
                first_el = elements[0]
                sample_text = first_el.get_text(strip=True)[:200] if first_el.get_text(strip=True) else None
                sample_html = str(first_el)[:500]

            # 대안 셀렉터 생성
            alternatives = []
            if not is_valid:
                alternatives = self._suggest_css_alternatives(soup, selector)

            # 신뢰도 계산
            confidence = self._calculate_selector_confidence(selector, match_count, html)

            return SelectorValidation(
                selector=selector,
                selector_type="css",
                is_valid=is_valid,
                match_count=match_count,
                sample_text=sample_text,
                sample_html=sample_html,
                alternatives=alternatives,
                confidence=confidence
            )

        except Exception as e:
            return SelectorValidation(
                selector=selector,
                selector_type="css",
                is_valid=False,
                match_count=0,
                error=f"CSS 셀렉터 파싱 오류: {str(e)}"
            )

    def validate_xpath_selector(self, html: str, selector: str) -> SelectorValidation:
        """XPath 셀렉터 검증"""
        try:
            tree = lxml_html.fromstring(html)
            elements = tree.xpath(selector)

            match_count = len(elements) if isinstance(elements, list) else (1 if elements else 0)
            is_valid = match_count > 0

            sample_text = None
            sample_html = None

            if isinstance(elements, list) and elements:
                first_el = elements[0]
                if hasattr(first_el, 'text_content'):
                    sample_text = first_el.text_content()[:200]
                if hasattr(first_el, 'tag'):
                    sample_html = lxml_html.tostring(first_el, encoding='unicode')[:500]

            # 대안 XPath 생성
            alternatives = []
            if not is_valid:
                alternatives = self._suggest_xpath_alternatives(tree, selector)

            confidence = self._calculate_selector_confidence(selector, match_count, html)

            return SelectorValidation(
                selector=selector,
                selector_type="xpath",
                is_valid=is_valid,
                match_count=match_count,
                sample_text=sample_text,
                sample_html=sample_html,
                alternatives=alternatives,
                confidence=confidence
            )

        except Exception as e:
            return SelectorValidation(
                selector=selector,
                selector_type="xpath",
                is_valid=False,
                match_count=0,
                error=f"XPath 파싱 오류: {str(e)}"
            )

    def _calculate_selector_confidence(self, selector: str, match_count: int, html: str) -> float:
        """셀렉터 신뢰도 계산 (0.0 ~ 1.0)"""
        if match_count == 0:
            return 0.0

        confidence = 0.5  # 기본 점수

        # ID 셀렉터는 높은 신뢰도
        if "#" in selector and "." not in selector.split("#")[1].split()[0]:
            confidence += 0.3

        # 구체적인 클래스 조합
        class_count = selector.count(".")
        if class_count >= 2:
            confidence += 0.1

        # 계층 구조가 있으면 더 구체적
        if ">" in selector or " " in selector:
            confidence += 0.1

        # 너무 많이 매칭되면 신뢰도 감소
        if match_count > 100:
            confidence -= 0.2
        elif match_count > 50:
            confidence -= 0.1

        # 정확히 1개 매칭은 좋은 신호
        if match_count == 1:
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

    def _suggest_css_alternatives(self, soup: BeautifulSoup, original: str) -> List[str]:
        """실패한 CSS 셀렉터에 대한 대안 제안"""
        alternatives = []

        # 원본 셀렉터에서 키워드 추출
        keywords = re.findall(r'[a-zA-Z_-]+', original.lower())

        # ID로 검색
        for keyword in keywords[:3]:
            elements = soup.find_all(id=re.compile(keyword, re.I))
            for el in elements[:2]:
                alt = f"#{el.get('id')}"
                if alt not in alternatives:
                    alternatives.append(alt)

        # 클래스로 검색
        for keyword in keywords[:3]:
            elements = soup.find_all(class_=re.compile(keyword, re.I))
            for el in elements[:2]:
                classes = el.get("class", [])
                if classes:
                    alt = f".{'.'.join(classes[:2])}"
                    if alt not in alternatives and len(alt) < 100:
                        alternatives.append(alt)

        return alternatives[:5]

    def _suggest_xpath_alternatives(self, tree, original: str) -> List[str]:
        """실패한 XPath 셀렉터에 대한 대안 제안"""
        alternatives = []

        # 원본에서 키워드 추출
        keywords = re.findall(r'[a-zA-Z_-]+', original.lower())

        for keyword in keywords[:3]:
            try:
                # ID 기반 XPath
                elements = tree.xpath(f"//*[contains(@id, '{keyword}')]")
                for el in elements[:2]:
                    el_id = el.get("id")
                    if el_id:
                        alt = f"//*[@id='{el_id}']"
                        if alt not in alternatives:
                            alternatives.append(alt)

                # class 기반 XPath
                elements = tree.xpath(f"//*[contains(@class, '{keyword}')]")
                for el in elements[:2]:
                    el_class = el.get("class")
                    if el_class:
                        first_class = el_class.split()[0]
                        alt = f"//*[contains(@class, '{first_class}')]"
                        if alt not in alternatives:
                            alternatives.append(alt)
            except:
                pass

        return alternatives[:5]

    async def validate_selectors(
        self,
        url: str,
        selectors: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        여러 셀렉터를 한번에 검증

        Args:
            url: 검증할 페이지 URL
            selectors: [{"selector": "...", "type": "css|xpath", "name": "optional_name"}, ...]

        Returns:
            {
                "url": "...",
                "fetch_success": True/False,
                "js_required": True/False,
                "validations": [SelectorValidation, ...],
                "summary": {"valid": 3, "invalid": 2}
            }
        """
        html, error = await self.fetch_html(url)

        if error:
            return {
                "url": url,
                "fetch_success": False,
                "error": error,
                "js_required": self._is_js_required(url),
                "validations": [],
                "summary": {"valid": 0, "invalid": len(selectors)}
            }

        validations = []
        for sel_info in selectors:
            selector = sel_info.get("selector", "")
            sel_type = sel_info.get("type", "css").lower()
            name = sel_info.get("name", "")

            if sel_type == "xpath":
                result = self.validate_xpath_selector(html, selector)
            else:
                result = self.validate_css_selector(html, selector)

            # 이름 추가
            result_dict = {
                "name": name,
                "selector": result.selector,
                "selector_type": result.selector_type,
                "is_valid": result.is_valid,
                "match_count": result.match_count,
                "sample_text": result.sample_text,
                "confidence": result.confidence,
                "alternatives": result.alternatives,
                "error": result.error
            }
            validations.append(result_dict)

        valid_count = sum(1 for v in validations if v["is_valid"])

        return {
            "url": url,
            "fetch_success": True,
            "js_required": self._is_js_required(url),
            "html_length": len(html),
            "validations": validations,
            "summary": {
                "valid": valid_count,
                "invalid": len(validations) - valid_count,
                "total": len(validations)
            }
        }

    async def analyze_page(self, url: str) -> PageAnalysis:
        """
        페이지 구조 분석 - 자동화에 유용한 요소들 추출
        """
        html, error = await self.fetch_html(url)

        if error:
            return PageAnalysis(
                url=url,
                title="",
                html_length=0,
                fetch_success=False,
                error=error
            )

        soup = BeautifulSoup(html, "lxml")

        # 페이지 제목
        title = soup.title.string if soup.title else ""

        # 폼 추출
        forms = []
        for form in soup.find_all("form")[:10]:
            forms.append({
                "id": form.get("id"),
                "action": form.get("action"),
                "method": form.get("method", "GET"),
                "selector": self._generate_selector(form)
            })

        # 입력 필드 추출
        inputs = []
        for inp in soup.find_all(["input", "textarea"])[:20]:
            inp_type = inp.get("type", "text")
            if inp_type in ["hidden", "submit"]:
                continue
            inputs.append({
                "type": inp_type,
                "id": inp.get("id"),
                "name": inp.get("name"),
                "placeholder": inp.get("placeholder"),
                "selector": self._generate_selector(inp)
            })

        # 버튼 추출
        buttons = []
        for btn in soup.find_all(["button", "input[type=submit]", "a"])[:20]:
            btn_text = btn.get_text(strip=True)[:50]
            if not btn_text:
                continue
            # 버튼처럼 보이는 요소 필터링
            classes = " ".join(btn.get("class", []))
            if btn.name == "a" and "btn" not in classes.lower() and "button" not in classes.lower():
                continue
            buttons.append({
                "text": btn_text,
                "type": btn.name,
                "id": btn.get("id"),
                "selector": self._generate_selector(btn)
            })

        # 리스트/반복 요소 추출
        lists = []
        for container in soup.find_all(["ul", "ol", "div", "section"])[:30]:
            children = container.find_all(recursive=False)
            if len(children) >= 3:
                # 동일 태그 자식이 3개 이상이면 리스트로 간주
                child_tags = [c.name for c in children]
                if len(set(child_tags)) <= 2:  # 태그 종류가 2개 이하
                    lists.append({
                        "container_selector": self._generate_selector(container),
                        "item_count": len(children),
                        "item_selector": self._generate_selector(children[0]) if children else "",
                        "sample_text": children[0].get_text(strip=True)[:100] if children else ""
                    })

        # 링크 추출 (외부 링크 제외)
        links = []
        parsed_url = urlparse(url)
        base_domain = parsed_url.netloc
        for a in soup.find_all("a", href=True)[:30]:
            href = a.get("href", "")
            text = a.get_text(strip=True)[:50]
            if not text or href.startswith("#") or href.startswith("javascript:"):
                continue
            # 외부 링크 제외
            if href.startswith("http") and base_domain not in href:
                continue
            links.append({
                "text": text,
                "href": href,
                "selector": self._generate_selector(a)
            })

        return PageAnalysis(
            url=url,
            title=title,
            html_length=len(html),
            fetch_success=True,
            forms=forms[:5],
            inputs=inputs[:10],
            buttons=buttons[:10],
            lists=lists[:5],
            links=links[:10]
        )

    def _generate_selector(self, element) -> str:
        """요소에 대한 고유 CSS 셀렉터 생성"""
        if not element:
            return ""

        # ID가 있으면 ID 사용
        el_id = element.get("id")
        if el_id and not re.search(r'\d{5,}', el_id):  # 긴 숫자 ID 제외
            return f"#{el_id}"

        # 의미있는 클래스 조합
        classes = element.get("class", [])
        meaningful_classes = [
            c for c in classes
            if not re.search(r'^[a-z]{1,2}\d|^\d|^_|^css', c, re.I)
            and len(c) > 2
        ]

        if meaningful_classes:
            tag = element.name
            class_selector = ".".join(meaningful_classes[:2])
            return f"{tag}.{class_selector}"

        # name 속성
        name = element.get("name")
        if name:
            return f'{element.name}[name="{name}"]'

        # placeholder
        placeholder = element.get("placeholder")
        if placeholder:
            return f'{element.name}[placeholder*="{placeholder[:20]}"]'

        # 부모 기반
        parent = element.parent
        if parent and parent.get("id"):
            return f"#{parent.get('id')} > {element.name}"

        return element.name

    async def suggest_selectors_for_action(
        self,
        url: str,
        action_type: str,
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        특정 액션에 적합한 셀렉터 추천

        Args:
            url: 대상 페이지 URL
            action_type: "search", "login", "list", "button", "form"
            context: 추가 컨텍스트 (예: "검색창", "로그인 버튼")

        Returns:
            [{"selector": "...", "confidence": 0.9, "description": "..."}, ...]
        """
        analysis = await self.analyze_page(url)

        if not analysis.fetch_success:
            return []

        suggestions = []
        context_lower = (context or "").lower()

        if action_type == "search":
            # 검색 입력창 찾기
            for inp in analysis.inputs:
                inp_lower = str(inp).lower()
                if any(kw in inp_lower for kw in ["search", "query", "검색", "q=", "keyword"]):
                    suggestions.append({
                        "selector": inp["selector"],
                        "confidence": 0.9,
                        "description": f"검색 입력창 (placeholder: {inp.get('placeholder', 'N/A')})"
                    })

            # 검색 버튼 찾기
            for btn in analysis.buttons:
                btn_lower = str(btn).lower()
                if any(kw in btn_lower for kw in ["search", "검색", "찾기", "조회"]):
                    suggestions.append({
                        "selector": btn["selector"],
                        "confidence": 0.85,
                        "description": f"검색 버튼: {btn.get('text', '')}"
                    })

        elif action_type == "login":
            # 로그인 폼 찾기
            for form in analysis.forms:
                form_str = str(form).lower()
                if any(kw in form_str for kw in ["login", "signin", "로그인"]):
                    suggestions.append({
                        "selector": form["selector"],
                        "confidence": 0.9,
                        "description": "로그인 폼"
                    })

            # 아이디/비밀번호 입력창
            for inp in analysis.inputs:
                inp_lower = str(inp).lower()
                if any(kw in inp_lower for kw in ["id", "email", "user", "아이디", "이메일"]):
                    suggestions.append({
                        "selector": inp["selector"],
                        "confidence": 0.85,
                        "description": f"아이디 입력: {inp.get('placeholder', inp.get('name', ''))}"
                    })
                elif any(kw in inp_lower for kw in ["password", "pw", "비밀번호"]):
                    suggestions.append({
                        "selector": inp["selector"],
                        "confidence": 0.85,
                        "description": "비밀번호 입력"
                    })

        elif action_type == "list":
            # 목록 요소 찾기
            for lst in analysis.lists:
                suggestions.append({
                    "selector": lst["item_selector"],
                    "confidence": 0.8,
                    "description": f"목록 항목 ({lst['item_count']}개): {lst.get('sample_text', '')[:50]}"
                })

        elif action_type == "button":
            # 컨텍스트에 맞는 버튼 찾기
            for btn in analysis.buttons:
                btn_text = btn.get("text", "").lower()
                if context_lower and context_lower in btn_text:
                    suggestions.append({
                        "selector": btn["selector"],
                        "confidence": 0.9,
                        "description": f"버튼: {btn.get('text', '')}"
                    })
                else:
                    suggestions.append({
                        "selector": btn["selector"],
                        "confidence": 0.6,
                        "description": f"버튼: {btn.get('text', '')}"
                    })

        # 신뢰도 순 정렬
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)

        return suggestions[:10]


# 싱글톤 인스턴스
selector_validator = SelectorValidator()


async def validate_workflow_selectors(
    url: str,
    blocks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    워크플로우 블록들의 셀렉터를 검증

    Returns:
        {
            "url": "...",
            "fetch_success": True/False,
            "blocks": [
                {
                    "block_id": "...",
                    "block_type": "...",
                    "selector": "...",
                    "is_valid": True/False,
                    "alternatives": [...],
                    ...
                }
            ],
            "summary": {"valid": 5, "invalid": 2}
        }
    """
    # 셀렉터가 있는 블록 추출
    selectors_to_validate = []
    block_mapping = []

    for block in blocks:
        block_type = block.get("id") or block.get("type", "")
        field_values = block.get("fieldValues", {}) or block.get("field_values", {})

        selector = field_values.get("selector")
        if selector:
            selector_type = field_values.get("selectorType", "css")
            selectors_to_validate.append({
                "selector": selector,
                "type": selector_type,
                "name": block.get("label", block_type)
            })
            block_mapping.append({
                "block_id": block.get("blockId", ""),
                "block_type": block_type,
                "label": block.get("label", "")
            })

    if not selectors_to_validate:
        return {
            "url": url,
            "fetch_success": True,
            "blocks": [],
            "summary": {"valid": 0, "invalid": 0, "total": 0}
        }

    # 검증 수행
    result = await selector_validator.validate_selectors(url, selectors_to_validate)

    # 블록 정보와 매핑
    blocks_result = []
    for i, validation in enumerate(result.get("validations", [])):
        block_info = block_mapping[i] if i < len(block_mapping) else {}
        blocks_result.append({
            **block_info,
            **validation
        })

    return {
        "url": url,
        "fetch_success": result.get("fetch_success", False),
        "js_required": result.get("js_required", False),
        "error": result.get("error"),
        "blocks": blocks_result,
        "summary": result.get("summary", {})
    }
