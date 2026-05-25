"""
지능형 셀렉터 추출 서비스
실제 HTML을 Claude에게 전달하여 정확한 셀렉터를 찾습니다.
"""

import re
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup
import httpx
import anthropic

from app.config import settings


class IntelligentSelectorService:
    """Claude를 활용한 정확한 셀렉터 추출"""

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._html_cache: Dict[str, str] = {}

    async def fetch_html(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """URL에서 HTML 가져오기"""
        if url in self._html_cache:
            return self._html_cache[url], None

        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                verify=False
            ) as client:
                response = await client.get(url, headers={
                    "User-Agent": self.USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                })
                response.raise_for_status()
                html = response.text
                self._html_cache[url] = html
                return html, None
        except Exception as e:
            return None, str(e)

    def extract_relevant_html(self, html: str, keywords: List[str], max_length: int = 15000) -> str:
        """관련 있는 HTML 부분만 추출 (토큰 절약)"""
        soup = BeautifulSoup(html, 'lxml')

        # 불필요한 태그 제거
        for tag in soup(['script', 'style', 'noscript', 'svg', 'path', 'meta', 'link', 'head']):
            tag.decompose()

        # 키워드 관련 요소 찾기
        relevant_parts = []

        # 폼, 입력 필드
        for form in soup.find_all('form')[:5]:
            relevant_parts.append(str(form)[:2000])

        # 입력 필드
        for inp in soup.find_all(['input', 'textarea', 'select'])[:15]:
            parent = inp.parent
            if parent:
                relevant_parts.append(str(parent)[:500])

        # 버튼
        for btn in soup.find_all(['button', 'a'])[:20]:
            text = btn.get_text(strip=True).lower()
            classes = ' '.join(btn.get('class', [])).lower()
            if any(kw in text or kw in classes for kw in ['검색', 'search', '로그인', 'login', '클릭', '확인', '조회', '버튼', 'btn', 'submit']):
                parent = btn.parent
                if parent:
                    relevant_parts.append(str(parent)[:500])

        # 키워드 포함 요소
        for keyword in keywords[:5]:
            elements = soup.find_all(string=re.compile(keyword, re.I))
            for el in elements[:3]:
                if el.parent:
                    relevant_parts.append(str(el.parent.parent or el.parent)[:500])

        # 리스트/반복 요소
        for container in soup.find_all(['ul', 'ol', 'table', 'div'])[:30]:
            children = container.find_all(recursive=False)
            if 3 <= len(children) <= 50:
                child_tags = [c.name for c in children[:10]]
                if len(set(child_tags)) <= 2:
                    relevant_parts.append(str(container)[:2000])
                    break

        # 가격, 숫자 관련 (주식/쇼핑)
        for el in soup.find_all(class_=re.compile(r'price|value|won|num|total|count', re.I))[:10]:
            relevant_parts.append(str(el.parent or el)[:300])

        # 결과 조합
        result = "\n\n<!-- Section -->\n".join(relevant_parts)

        # 길이 제한
        if len(result) > max_length:
            result = result[:max_length] + "\n... (truncated)"

        return result

    async def analyze_page_for_task(
        self,
        url: str,
        task_description: str,
        target_data: List[str] = None
    ) -> Dict[str, Any]:
        """
        페이지를 분석하여 작업에 필요한 셀렉터 추출

        Args:
            url: 분석할 페이지 URL
            task_description: 작업 설명 (예: "삼성전자 주가 정보 추출")
            target_data: 추출할 데이터 목록 (예: ["현재가", "거래량", "시가총액"])

        Returns:
            {
                "url": "...",
                "success": True,
                "selectors": {
                    "현재가": {"selector": "#price", "type": "css", "sample": "75,000"},
                    ...
                },
                "page_info": {...}
            }
        """
        html, error = await self.fetch_html(url)

        if error:
            return {
                "url": url,
                "success": False,
                "error": f"페이지 로드 실패: {error}",
                "selectors": {}
            }

        # 키워드 추출
        keywords = [task_description]
        if target_data:
            keywords.extend(target_data)

        # 관련 HTML 추출
        relevant_html = self.extract_relevant_html(html, keywords)

        # Claude에게 셀렉터 분석 요청
        prompt = f"""당신은 웹 스크래핑 전문가입니다. 아래 HTML에서 정확한 CSS 셀렉터를 찾아주세요.

## 작업 설명
{task_description}

## 추출할 데이터
{json.dumps(target_data or ["주요 데이터"], ensure_ascii=False)}

## 실제 HTML (일부)
```html
{relevant_html}
```

## 응답 형식 (JSON만 출력)
{{
    "page_title": "페이지 제목",
    "selectors": {{
        "데이터명1": {{
            "selector": "정확한 CSS 셀렉터",
            "type": "css",
            "description": "이 셀렉터가 가리키는 요소 설명",
            "sample_value": "HTML에서 찾은 실제 값 (있다면)",
            "confidence": 0.95
        }},
        "데이터명2": {{ ... }}
    }},
    "forms": [
        {{
            "purpose": "검색폼/로그인폼 등",
            "input_selector": "입력창 셀렉터",
            "submit_selector": "제출 버튼 셀렉터"
        }}
    ],
    "lists": [
        {{
            "purpose": "목록 설명",
            "container_selector": "컨테이너 셀렉터",
            "item_selector": "개별 항목 셀렉터",
            "item_count": 10
        }}
    ],
    "notes": "특이사항 (JS 렌더링 필요 등)"
}}

중요:
1. HTML에서 실제로 존재하는 셀렉터만 반환하세요
2. 추측하지 마세요. HTML에 없으면 "not_found"로 표시
3. ID 셀렉터 > 고유한 클래스 > 복합 셀렉터 순으로 선호
4. confidence는 셀렉터의 정확도 (0.0-1.0)"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # JSON 추출
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "url": url,
                    "success": True,
                    "selectors": result.get("selectors", {}),
                    "forms": result.get("forms", []),
                    "lists": result.get("lists", []),
                    "page_title": result.get("page_title", ""),
                    "notes": result.get("notes", "")
                }

        except Exception as e:
            print(f"[IntelligentSelector] 분석 오류: {e}")

        return {
            "url": url,
            "success": False,
            "error": "분석 실패",
            "selectors": {}
        }

    async def analyze_workflow_urls(
        self,
        prompt: str,
        urls: List[str]
    ) -> Dict[str, Any]:
        """
        워크플로우에서 사용되는 여러 URL을 분석

        Args:
            prompt: 사용자 요청 (작업 설명)
            urls: 분석할 URL 목록

        Returns:
            {
                "analyses": [
                    {"url": "...", "selectors": {...}},
                    ...
                ],
                "combined_context": "AI 프롬프트에 포함할 컨텍스트"
            }
        """
        analyses = []

        # 프롬프트에서 타겟 데이터 추출
        target_data = self._extract_target_data(prompt)

        # 각 URL 분석 (병렬)
        tasks = [
            self.analyze_page_for_task(url, prompt, target_data)
            for url in urls[:5]  # 최대 5개 URL
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, dict):
                analyses.append(result)

        # 통합 컨텍스트 생성
        combined_context = self._build_combined_context(analyses)

        return {
            "analyses": analyses,
            "combined_context": combined_context
        }

    def _extract_target_data(self, prompt: str) -> List[str]:
        """프롬프트에서 추출할 데이터 항목 추출"""
        targets = []

        # 주식 관련
        stock_keywords = ["현재가", "주가", "가격", "시가", "고가", "저가", "종가",
                          "거래량", "시가총액", "등락률", "전일대비", "PER", "PBR", "배당"]
        for kw in stock_keywords:
            if kw in prompt:
                targets.append(kw)

        # 쇼핑 관련
        shopping_keywords = ["상품명", "제품명", "가격", "할인가", "원가", "배송", "리뷰", "평점"]
        for kw in shopping_keywords:
            if kw in prompt:
                targets.append(kw)

        # 뉴스/게시판 관련
        content_keywords = ["제목", "본문", "내용", "작성자", "날짜", "조회수", "댓글"]
        for kw in content_keywords:
            if kw in prompt:
                targets.append(kw)

        return targets if targets else ["주요 데이터"]

    def _build_combined_context(self, analyses: List[Dict]) -> str:
        """분석 결과를 AI 프롬프트용 컨텍스트로 변환"""
        context = ""

        for analysis in analyses:
            if not analysis.get("success"):
                context += f"\n## ⚠️ {analysis.get('url', 'URL')} - 분석 실패\n"
                context += f"오류: {analysis.get('error', '알 수 없음')}\n"
                continue

            url = analysis.get("url", "")
            context += f"\n## 📄 {url} 분석 결과\n"

            if analysis.get("notes"):
                context += f"⚠️ {analysis['notes']}\n"

            # 셀렉터
            selectors = analysis.get("selectors", {})
            if selectors:
                context += "\n### 검증된 셀렉터:\n"
                for name, info in selectors.items():
                    if isinstance(info, dict):
                        selector = info.get("selector", "not_found")
                        confidence = info.get("confidence", 0)
                        sample = info.get("sample_value", "")
                        if selector != "not_found":
                            context += f"- **{name}**: `{selector}` "
                            if sample:
                                context += f"(예: {sample[:30]})"
                            context += f" [신뢰도: {confidence:.0%}]\n"

            # 폼
            forms = analysis.get("forms", [])
            if forms:
                context += "\n### 폼:\n"
                for form in forms:
                    context += f"- {form.get('purpose', '폼')}: "
                    context += f"입력=`{form.get('input_selector', '')}`, "
                    context += f"제출=`{form.get('submit_selector', '')}`\n"

            # 리스트
            lists = analysis.get("lists", [])
            if lists:
                context += "\n### 목록/반복 요소:\n"
                for lst in lists:
                    context += f"- {lst.get('purpose', '목록')}: "
                    context += f"항목=`{lst.get('item_selector', '')}` "
                    context += f"({lst.get('item_count', '?')}개)\n"

        context += """
## ⚠️ 셀렉터 사용 규칙:
1. 위에 나열된 **검증된 셀렉터**만 사용하세요
2. 셀렉터를 **절대로 추측하거나 만들어내지 마세요**
3. 필요한 셀렉터가 없으면 해당 단계를 **생략**하세요
4. 신뢰도가 낮은 셀렉터는 주의해서 사용하세요
"""

        return context

    async def validate_and_fix_selectors(
        self,
        url: str,
        selectors: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        셀렉터 검증 및 수정

        Args:
            url: 검증할 페이지 URL
            selectors: {"이름": "셀렉터", ...}

        Returns:
            {
                "valid": ["이름1", "이름2"],
                "invalid": ["이름3"],
                "fixed": {"이름3": "수정된 셀렉터"},
                "suggestions": {...}
            }
        """
        html, error = await self.fetch_html(url)

        if error:
            return {
                "success": False,
                "error": error,
                "valid": [],
                "invalid": list(selectors.keys()),
                "fixed": {}
            }

        soup = BeautifulSoup(html, 'lxml')

        valid = []
        invalid = []
        fixed = {}

        for name, selector in selectors.items():
            try:
                elements = soup.select(selector)
                if elements:
                    valid.append(name)
                else:
                    invalid.append(name)
            except:
                invalid.append(name)

        # 실패한 셀렉터 수정 시도
        if invalid:
            relevant_html = self.extract_relevant_html(html, invalid)

            fix_prompt = f"""다음 CSS 셀렉터들이 페이지에서 작동하지 않습니다. HTML을 분석하여 올바른 셀렉터를 찾아주세요.

## 실패한 셀렉터
{json.dumps({name: selectors[name] for name in invalid}, ensure_ascii=False, indent=2)}

## HTML (일부)
```html
{relevant_html[:10000]}
```

## 응답 (JSON)
{{
    "fixed_selectors": {{
        "이름": "수정된 셀렉터 또는 null (찾을 수 없음)"
    }}
}}"""

            try:
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": fix_prompt}]
                )

                json_match = re.search(r'\{[\s\S]*\}', response.content[0].text)
                if json_match:
                    result = json.loads(json_match.group())
                    fixed = {k: v for k, v in result.get("fixed_selectors", {}).items() if v}

            except Exception as e:
                print(f"[IntelligentSelector] 셀렉터 수정 오류: {e}")

        return {
            "success": True,
            "valid": valid,
            "invalid": [i for i in invalid if i not in fixed],
            "fixed": fixed
        }


# 싱글톤
intelligent_selector = IntelligentSelectorService()
