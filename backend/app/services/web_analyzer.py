"""
Web Analyzer Service
웹사이트를 분석하여 셀렉터와 구조를 파악하는 서비스
"""

import httpx
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional
import re
import json
from app.config import settings


class WebAnalyzer:
    """웹사이트 분석 및 셀렉터 추출"""

    # 일반적인 웹사이트 URL 패턴
    SITE_PATTERNS = {
        "naver_news": {
            "pattern": r"(네이버\s*뉴스|naver\s*news)",
            "url": "https://news.naver.com",
            "type": "news",
            "requires_js": True,
        },
        "naver_search": {
            "pattern": r"(네이버\s*검색|naver\s*search)",
            "url": "https://search.naver.com/search.naver",
            "type": "search",
            "requires_js": False,
        },
        "google_search": {
            "pattern": r"(구글\s*검색|google\s*search)",
            "url": "https://www.google.com/search",
            "type": "search",
            "requires_js": False,
        },
        "coupang": {
            "pattern": r"(쿠팡|coupang)",
            "url": "https://www.coupang.com",
            "type": "shopping",
            "requires_js": True,
        },
        "gmarket": {
            "pattern": r"(지마켓|gmarket)",
            "url": "https://www.gmarket.co.kr",
            "type": "shopping",
            "requires_js": True,
        },
    }

    @classmethod
    async def analyze_prompt_for_url(cls, prompt: str) -> Dict[str, Any]:
        """프롬프트에서 URL과 사이트 정보 추출"""
        prompt_lower = prompt.lower()

        # URL이 직접 포함되어 있는지 확인
        url_match = re.search(r'https?://[^\s]+', prompt)
        if url_match:
            url = url_match.group()
            return {
                "url": url,
                "requires_js": True,  # 기본적으로 JS 필요로 가정
                "type": "custom",
            }

        # 알려진 사이트 패턴 매칭
        for site_key, site_info in cls.SITE_PATTERNS.items():
            if re.search(site_info["pattern"], prompt_lower, re.IGNORECASE):
                return {
                    "url": site_info["url"],
                    "requires_js": site_info["requires_js"],
                    "type": site_info["type"],
                    "site_key": site_key,
                }

        return {"url": None, "requires_js": True, "type": "unknown"}

    @classmethod
    async def fetch_page(cls, url: str, timeout: int = 10) -> Optional[str]:
        """웹페이지 HTML 가져오기"""
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                }
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return None

    @classmethod
    def extract_page_structure(cls, html: str, max_elements: int = 50) -> Dict[str, Any]:
        """HTML에서 주요 구조 추출"""
        soup = BeautifulSoup(html, 'html.parser')

        # 스크립트, 스타일 제거
        for tag in soup(['script', 'style', 'noscript', 'iframe']):
            tag.decompose()

        structure = {
            "title": soup.title.string if soup.title else "",
            "forms": [],
            "inputs": [],
            "buttons": [],
            "links": [],
            "lists": [],
            "articles": [],
        }

        # 폼 추출
        for form in soup.find_all('form')[:5]:
            form_info = {
                "action": form.get('action', ''),
                "method": form.get('method', 'get'),
                "id": form.get('id', ''),
                "class": ' '.join(form.get('class', [])),
            }
            structure["forms"].append(form_info)

        # 입력 필드 추출
        for inp in soup.find_all(['input', 'textarea'])[:20]:
            if inp.get('type') in ['hidden', 'submit']:
                continue
            inp_info = {
                "type": inp.get('type', 'text'),
                "name": inp.get('name', ''),
                "id": inp.get('id', ''),
                "class": ' '.join(inp.get('class', [])),
                "placeholder": inp.get('placeholder', ''),
                "selector": cls._generate_selector(inp),
            }
            structure["inputs"].append(inp_info)

        # 버튼 추출
        for btn in soup.find_all(['button', 'input[type=submit]', 'a'])[:20]:
            if btn.name == 'a' and not any(kw in (btn.get_text() or '').lower() for kw in ['검색', '로그인', '확인', 'search', 'login', 'submit']):
                continue
            btn_info = {
                "text": btn.get_text(strip=True)[:50],
                "id": btn.get('id', ''),
                "class": ' '.join(btn.get('class', [])),
                "selector": cls._generate_selector(btn),
            }
            if btn_info["text"] or btn_info["id"]:
                structure["buttons"].append(btn_info)

        # 리스트/반복 요소 추출
        for container in soup.find_all(['ul', 'ol', 'div'])[:30]:
            children = container.find_all(recursive=False)
            if len(children) >= 3:
                # 비슷한 구조의 자식이 3개 이상이면 리스트로 간주
                child_classes = [' '.join(c.get('class', [])) for c in children[:5]]
                if len(set(child_classes)) <= 2:  # 클래스가 비슷하면
                    list_info = {
                        "container_selector": cls._generate_selector(container),
                        "item_selector": cls._generate_selector(children[0]) if children else "",
                        "item_count": len(children),
                        "sample_text": children[0].get_text(strip=True)[:100] if children else "",
                    }
                    structure["lists"].append(list_info)
                    if len(structure["lists"]) >= 10:
                        break

        # 기사/콘텐츠 영역 추출
        for article in soup.find_all(['article', 'div'])[:20]:
            classes = ' '.join(article.get('class', []))
            if any(kw in classes.lower() for kw in ['article', 'news', 'item', 'card', 'post', 'content']):
                article_info = {
                    "selector": cls._generate_selector(article),
                    "class": classes,
                    "has_link": bool(article.find('a')),
                    "has_image": bool(article.find('img')),
                    "sample_text": article.get_text(strip=True)[:200],
                }
                structure["articles"].append(article_info)
                if len(structure["articles"]) >= 10:
                    break

        return structure

    @classmethod
    def _generate_selector(cls, element) -> str:
        """요소에서 CSS 셀렉터 생성"""
        if element.get('id'):
            return f"#{element['id']}"

        classes = element.get('class', [])
        if classes:
            # 의미있는 클래스 선택
            meaningful_classes = [c for c in classes if len(c) > 2 and not c.startswith('_')]
            if meaningful_classes:
                return f"{element.name}.{'.'.join(meaningful_classes[:2])}"

        # 부모 기반 셀렉터
        parent = element.parent
        if parent and parent.name != '[document]':
            parent_selector = ""
            if parent.get('id'):
                parent_selector = f"#{parent['id']}"
            elif parent.get('class'):
                parent_selector = f"{parent.name}.{parent['class'][0]}"

            if parent_selector:
                return f"{parent_selector} > {element.name}"

        return element.name

    @classmethod
    async def analyze_with_claude(cls, prompt: str, url: str, page_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Claude를 사용해 페이지 구조 분석 및 셀렉터 추천"""
        import anthropic

        if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == "your-anthropic-api-key":
            # API 키 없으면 기본 분석 반환
            return cls._generate_default_analysis(prompt, url, page_structure)

        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            system_prompt = """당신은 웹 스크래핑 전문가입니다. 사용자의 요청과 웹페이지 구조를 분석하여:
1. 가장 적합한 CSS 셀렉터를 찾아냅니다
2. requests vs Selenium 중 어느 것이 적합한지 판단합니다
3. 자동화에 필요한 모든 필드 값을 제안합니다

응답은 반드시 다음 JSON 형식으로:
{
    "recommended_method": "selenium" 또는 "requests",
    "reason": "방법 선택 이유",
    "steps": [
        {
            "action": "액션 종류 (open-site, click, input-text, extract-list, save-excel 등)",
            "description": "이 단계 설명",
            "field_values": {
                "필드명": "값"
            }
        }
    ],
    "main_selectors": {
        "search_input": "검색창 셀렉터",
        "search_button": "검색 버튼 셀렉터",
        "result_list": "결과 목록 컨테이너 셀렉터",
        "result_item": "개별 결과 항목 셀렉터",
        "title": "제목 셀렉터",
        "link": "링크 셀렉터"
    }
}"""

            message = client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"""사용자 요청: {prompt}

대상 URL: {url}

페이지 구조:
- 제목: {page_structure.get('title', '')}
- 입력 필드: {json.dumps(page_structure.get('inputs', [])[:10], ensure_ascii=False)}
- 버튼: {json.dumps(page_structure.get('buttons', [])[:10], ensure_ascii=False)}
- 리스트 요소: {json.dumps(page_structure.get('lists', [])[:5], ensure_ascii=False)}
- 기사/콘텐츠: {json.dumps(page_structure.get('articles', [])[:5], ensure_ascii=False)}

위 정보를 바탕으로 자동화 단계와 셀렉터를 분석해주세요."""
                    }
                ]
            )

            response_text = message.content[0].text

            # JSON 추출
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                return json.loads(json_match.group())

            return cls._generate_default_analysis(prompt, url, page_structure)

        except Exception as e:
            print(f"Claude analysis error: {e}")
            return cls._generate_default_analysis(prompt, url, page_structure)

    @classmethod
    def _generate_default_analysis(cls, prompt: str, url: str, page_structure: Dict[str, Any]) -> Dict[str, Any]:
        """기본 분석 결과 생성 (API 없을 때)"""
        # 프롬프트에서 키워드 추출
        search_keywords = []
        for word in ["뉴스", "검색", "크롤링", "수집", "가격", "상품"]:
            if word in prompt:
                search_keywords.append(word)

        # 페이지 구조에서 셀렉터 추출
        search_input = ""
        search_button = ""
        result_list = ""
        result_item = ""

        if page_structure.get("inputs"):
            for inp in page_structure["inputs"]:
                if any(kw in (inp.get("placeholder", "") + inp.get("name", "")).lower()
                       for kw in ["search", "query", "검색", "keyword"]):
                    search_input = inp.get("selector", "")
                    break
            if not search_input and page_structure["inputs"]:
                search_input = page_structure["inputs"][0].get("selector", "input")

        if page_structure.get("buttons"):
            for btn in page_structure["buttons"]:
                if any(kw in btn.get("text", "").lower() for kw in ["검색", "search"]):
                    search_button = btn.get("selector", "")
                    break

        if page_structure.get("lists"):
            best_list = max(page_structure["lists"], key=lambda x: x.get("item_count", 0))
            result_list = best_list.get("container_selector", "")
            result_item = best_list.get("item_selector", "")

        return {
            "recommended_method": "selenium",
            "reason": "동적 콘텐츠 로딩이 필요할 수 있음",
            "steps": [
                {
                    "action": "open-site",
                    "description": "대상 사이트 열기",
                    "field_values": {"url": url}
                },
                {
                    "action": "wait-page-load",
                    "description": "페이지 로드 대기",
                    "field_values": {"timeout": "10"}
                },
                {
                    "action": "input-text",
                    "description": "검색어 입력",
                    "field_values": {
                        "selector": search_input or "input[type=search]",
                        "text": search_keywords[0] if search_keywords else "검색어",
                        "clear": "clear"
                    }
                },
                {
                    "action": "click",
                    "description": "검색 버튼 클릭",
                    "field_values": {"selector": search_button or "button[type=submit]"}
                },
                {
                    "action": "wait",
                    "description": "결과 로딩 대기",
                    "field_values": {"seconds": "2"}
                },
                {
                    "action": "extract-list",
                    "description": "결과 목록 추출",
                    "field_values": {
                        "selector": result_item or ".item",
                        "fields": "title, link",
                        "variable": "results"
                    }
                },
                {
                    "action": "save-excel",
                    "description": "엑셀 파일로 저장",
                    "field_values": {
                        "variable": "results",
                        "filename": "result.xlsx",
                        "mode": "overwrite"
                    }
                }
            ],
            "main_selectors": {
                "search_input": search_input or "input[type=search]",
                "search_button": search_button or "button[type=submit]",
                "result_list": result_list or ".results",
                "result_item": result_item or ".result-item",
                "title": ".title",
                "link": "a"
            }
        }


# 사이트별 기본 셀렉터 정보 (JavaScript 렌더링 사이트 포함)
SITE_SELECTORS = {
    "naver_finance": {
        "url": "https://finance.naver.com",
        "description": "네이버 증권 - JavaScript 렌더링 필요",
        "search_input": "#stock_items",
        "search_button": ".btn_search",
        # 개별 종목 페이지 (예: finance.naver.com/item/main.naver?code=005930)
        "stock_name": ".wrap_company h2 a",  # 종목명
        "current_price": "#_nowVal, .no_today .blind",  # 현재가
        "price_change": "#_diff .blind, .no_exday .blind",  # 전일대비
        "price_rate": "#_rate .blind, .no_exday em.bu, .no_exday em.no",  # 등락률
        "trading_volume": "#_quant, .no_info tr:nth-child(1) td",  # 거래량
        "market_cap": ".no_info tr:nth-child(3) td",  # 시가총액
        "high_price": ".no_info tr:nth-child(1) td:nth-child(2)",  # 고가
        "low_price": ".no_info tr:nth-child(2) td:nth-child(2)",  # 저가
        "open_price": ".no_info tr:nth-child(1) td:nth-child(1)",  # 시가
        # 차트 및 기타
        "chart_area": "#area_chart",
        "news_list": ".sub_section.news_section li",
        "recommended_method": "selenium",
        "requires_js": True,
    },
    "naver_news": {
        "url": "https://news.naver.com",
        "description": "네이버 뉴스",
        "search_input": "#newsSearchInput",
        "search_button": ".btn_search",
        "article_list": ".news_area, .list_news li",
        "article_title": ".news_tit, .tit",
        "article_link": "a.news_tit, a",
        "article_desc": ".news_dsc, .dsc",
        "recommended_method": "selenium",
        "requires_js": True,
    },
    "naver_search": {
        "url": "https://search.naver.com/search.naver",
        "description": "네이버 검색",
        "search_input": "#nx_query",
        "search_button": ".bt_search",
        "result_list": ".lst_total li, .news_wrap",
        "result_title": ".api_txt_lines, .news_tit",
        "result_link": "a.api_txt_lines, a",
        "recommended_method": "requests",
        "requires_js": False,
    },
    "naver_cafe": {
        "url": "https://cafe.naver.com",
        "description": "네이버 카페 - JavaScript 렌더링 필요",
        "search_input": "#topLayerQueryInput",
        "search_button": ".btn-search-green",
        "post_list": ".article-board tbody tr",
        "post_title": ".article",
        "post_link": ".article a",
        "post_author": ".td_name .p-nick",
        "post_date": ".td_date",
        "recommended_method": "selenium",
        "requires_js": True,
    },
    "coupang": {
        "url": "https://www.coupang.com",
        "description": "쿠팡 - JavaScript 렌더링 필요",
        "search_input": ".search-input, input[name='q']",
        "search_button": ".search-btn, button.search-submit",
        "product_list": ".search-product, li.search-product, .baby-product-list li",
        "product_title": ".name, .descriptions .name",
        "product_price": ".price-value, .price",
        "product_link": "a.search-product-link, a.baby-product-link",
        "product_image": ".search-product-wrap img",
        "recommended_method": "selenium",
        "requires_js": True,
    },
    "gmarket": {
        "url": "https://www.gmarket.co.kr",
        "description": "지마켓 - JavaScript 렌더링 필요",
        "search_input": "#keyword",
        "search_button": ".btn_sch",
        "product_list": ".list__item, .box__item-container",
        "product_title": ".text__item-title",
        "product_price": ".text__value",
        "product_link": "a.link__item",
        "recommended_method": "selenium",
        "requires_js": True,
    },
}
