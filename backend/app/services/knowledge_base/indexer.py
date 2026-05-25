"""
Code Indexer - Python 자동화 코드에서 메타데이터 추출
"""

import os
import re
import ast
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class AutomationProject:
    """자동화 프로젝트 메타데이터"""
    id: str
    name: str  # 폴더명
    path: str  # 전체 경로

    # 코드 분석 결과
    libraries: List[str]  # 사용된 라이브러리
    sites: List[str]  # 대상 사이트 (URL에서 추출)
    actions: List[str]  # 수행 작업 (click, input, extract 등)
    selectors: List[str]  # CSS/XPath 셀렉터

    # 분류
    category: str  # 네이버, 쿠팡, 인스타그램 등
    subcategory: str  # 크롤링, 업로드, 로그인 등

    # 코드 정보
    main_code: str  # 주요 코드 (요약)
    full_code: str  # 전체 코드
    file_count: int  # Python 파일 개수
    total_lines: int  # 총 라인 수

    # 메타
    created_at: str
    description: str  # AI가 생성한 설명


class CodeIndexer:
    """Python 자동화 코드 인덱서"""

    # 사이트 패턴 매칭
    SITE_PATTERNS = {
        "naver": ["naver.com", "네이버", "naver"],
        "coupang": ["coupang.com", "쿠팡", "coupang"],
        "instagram": ["instagram.com", "인스타", "instagram", "인스타그램"],
        "facebook": ["facebook.com", "페이스북", "facebook", "페북"],
        "twitter": ["twitter.com", "트위터", "twitter", "x.com"],
        "youtube": ["youtube.com", "유튜브", "youtube"],
        "carrot": ["daangn", "당근", "carrot", "당근마켓"],
        "bunjang": ["bunjang", "번개장터", "번장"],
        "joonggonara": ["중고나라", "joonggo", "중나"],
        "dcinside": ["dcinside", "디시", "디시인사이드"],
        "discord": ["discord", "디스코드"],
        "telegram": ["telegram", "텔레그램"],
        "band": ["band.us", "밴드", "band"],
        "cafe24": ["cafe24", "카페24"],
        "smartstore": ["smartstore", "스마트스토어", "스토어팜"],
        "gmarket": ["gmarket", "지마켓", "옥션", "auction"],
        "soop": ["soop", "afreeca", "아프리카", "숲"],
    }

    # 카테고리 분류
    CATEGORY_KEYWORDS = {
        "크롤링": ["크롤링", "crawl", "scrape", "추출", "수집", "crw"],
        "업로드": ["업로드", "upload", "등록", "글쓰기", "포스팅", "posting"],
        "로그인": ["로그인", "login", "signin", "인증"],
        "댓글": ["댓글", "comment", "reply", "대댓글"],
        "좋아요": ["좋아요", "like", "추천", "공감"],
        "팔로우": ["팔로우", "follow", "구독", "이웃"],
        "채팅": ["채팅", "chat", "메시지", "톡", "쪽지"],
        "매크로": ["매크로", "macro", "자동화", "반복"],
        "트래픽": ["트래픽", "traffic", "조회수", "방문"],
    }

    # 주요 라이브러리
    KNOWN_LIBRARIES = [
        "selenium", "requests", "beautifulsoup4", "bs4", "pyautogui",
        "pyperclip", "openpyxl", "pandas", "pymysql", "openai",
        "undetected_chromedriver", "pyqt5", "tkinter", "PIL", "pillow"
    ]

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.projects: List[AutomationProject] = []

    def scan_all_projects(self) -> List[AutomationProject]:
        """모든 프로젝트 스캔"""
        print(f"[Indexer] 스캔 시작: {self.base_path}")

        for folder in self.base_path.iterdir():
            if folder.is_dir() and not folder.name.startswith(('.', '_')):
                try:
                    project = self._analyze_project(folder)
                    if project:
                        self.projects.append(project)
                        print(f"  [+] {project.name} - {project.category}/{project.subcategory}")
                except Exception as e:
                    print(f"  [!] {folder.name} 분석 실패: {e}")

        print(f"[Indexer] 완료: {len(self.projects)}개 프로젝트")
        return self.projects

    def _analyze_project(self, folder: Path) -> Optional[AutomationProject]:
        """개별 프로젝트 분석"""
        py_files = list(folder.glob("*.py"))
        if not py_files:
            return None

        # 코드 수집
        all_code = ""
        main_code = ""
        total_lines = 0

        for py_file in py_files:
            try:
                code = py_file.read_text(encoding='utf-8', errors='ignore')
                all_code += f"\n# === {py_file.name} ===\n{code}"
                total_lines += len(code.splitlines())

                # main.py 또는 Macro.py 우선
                if py_file.name.lower() in ['main.py', 'macro.py']:
                    main_code = code
            except:
                pass

        if not all_code.strip():
            return None

        if not main_code:
            main_code = all_code[:5000]  # 첫 5000자

        # 분석
        libraries = self._extract_libraries(all_code)
        sites = self._extract_sites(all_code, folder.name)
        actions = self._extract_actions(all_code)
        selectors = self._extract_selectors(all_code)
        category = self._determine_category(folder.name, all_code)
        subcategory = self._determine_subcategory(folder.name, all_code)
        description = self._generate_description(folder.name, libraries, sites, actions)

        return AutomationProject(
            id=f"proj_{hashlib.md5(str(folder).encode()).hexdigest()[:12]}",
            name=folder.name,
            path=str(folder),
            libraries=libraries,
            sites=sites,
            actions=actions,
            selectors=selectors[:100],  # 최대 100개
            category=category,
            subcategory=subcategory,
            main_code=main_code[:20000],  # 최대 20,000자
            full_code=all_code[:50000],  # 최대 50,000자
            file_count=len(py_files),
            total_lines=total_lines,
            created_at=datetime.now().isoformat(),
            description=description
        )

    def _extract_libraries(self, code: str) -> List[str]:
        """사용된 라이브러리 추출"""
        libraries = set()

        # import 문 파싱
        import_pattern = r'^(?:from|import)\s+([\w\.]+)'
        for match in re.finditer(import_pattern, code, re.MULTILINE):
            lib = match.group(1).split('.')[0].lower()
            if lib in self.KNOWN_LIBRARIES or lib in ['selenium', 'requests', 'bs4']:
                libraries.add(lib)

        # 특정 패턴 감지
        if 'webdriver' in code.lower():
            libraries.add('selenium')
        if 'BeautifulSoup' in code:
            libraries.add('beautifulsoup4')
        if 'pyautogui' in code.lower():
            libraries.add('pyautogui')
        if 'undetected_chromedriver' in code:
            libraries.add('undetected_chromedriver')

        return list(libraries)

    def _extract_sites(self, code: str, folder_name: str) -> List[str]:
        """대상 사이트 추출"""
        sites = set()
        code_lower = code.lower()
        folder_lower = folder_name.lower()

        for site, patterns in self.SITE_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in code_lower or pattern.lower() in folder_lower:
                    sites.add(site)
                    break

        # URL 패턴 추출
        url_pattern = r'https?://(?:www\.)?([a-zA-Z0-9-]+)\.'
        for match in re.finditer(url_pattern, code):
            domain = match.group(1).lower()
            for site, patterns in self.SITE_PATTERNS.items():
                if any(domain in p.lower() for p in patterns):
                    sites.add(site)

        return list(sites) if sites else ["기타"]

    def _extract_actions(self, code: str) -> List[str]:
        """수행 작업 추출"""
        actions = set()
        code_lower = code.lower()

        action_patterns = {
            "click": [".click()", "click(", "클릭"],
            "input": ["send_keys(", "input", "입력", "작성"],
            "extract": ["find_element", "find_all", "추출", "크롤링", "수집"],
            "login": ["login", "로그인", "signin"],
            "upload": ["upload", "업로드", "등록", "글쓰기"],
            "download": ["download", "다운로드", "저장"],
            "scroll": ["scroll", "스크롤"],
            "wait": ["sleep(", "wait", "대기", "딜레이"],
            "screenshot": ["screenshot", "스크린샷", "캡쳐"],
        }

        for action, patterns in action_patterns.items():
            if any(p in code_lower for p in patterns):
                actions.add(action)

        return list(actions)

    def _extract_selectors(self, code: str) -> List[str]:
        """CSS/XPath 셀렉터 추출"""
        selectors = []

        # CSS 셀렉터 패턴
        css_patterns = [
            r'By\.CSS_SELECTOR,\s*["\']([^"\']+)["\']',
            r'By\.ID,\s*["\']([^"\']+)["\']',
            r'By\.CLASS_NAME,\s*["\']([^"\']+)["\']',
            r'\.find_element\([^)]*["\']([^"\']+)["\']',
            r'document\.querySelector\(["\']([^"\']+)["\']',
        ]

        for pattern in css_patterns:
            for match in re.finditer(pattern, code):
                selector = match.group(1)
                if len(selector) > 2 and selector not in selectors:
                    selectors.append(selector)

        return selectors[:20]

    def _determine_category(self, folder_name: str, code: str) -> str:
        """메인 카테고리 결정"""
        folder_lower = folder_name.lower()
        code_lower = code.lower()

        for site, patterns in self.SITE_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in folder_lower:
                    return site

        # 코드에서 검색
        for site, patterns in self.SITE_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in code_lower:
                    return site

        return "기타"

    def _determine_subcategory(self, folder_name: str, code: str) -> str:
        """서브 카테고리 결정"""
        folder_lower = folder_name.lower()
        code_lower = code.lower()

        for subcat, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in folder_lower or keyword in code_lower:
                    return subcat

        return "자동화"

    def _generate_description(self, name: str, libraries: List[str],
                             sites: List[str], actions: List[str]) -> str:
        """프로젝트 설명 생성"""
        lib_str = ", ".join(libraries[:3]) if libraries else "Python"
        site_str = ", ".join(sites[:2]) if sites else "웹사이트"
        action_str = ", ".join(actions[:3]) if actions else "자동화"

        return f"{site_str} 대상 {action_str} 자동화. {lib_str} 사용."

    def save_index(self, output_path: str):
        """인덱스를 JSON으로 저장"""
        data = [asdict(p) for p in self.projects]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[Indexer] 인덱스 저장: {output_path}")

    def load_index(self, input_path: str) -> List[AutomationProject]:
        """JSON에서 인덱스 로드"""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.projects = [AutomationProject(**p) for p in data]
        return self.projects


# CLI 실행
if __name__ == "__main__":
    import sys

    base_path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\user\Desktop\프로그램 파일"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "automation_index.json"

    indexer = CodeIndexer(base_path)
    projects = indexer.scan_all_projects()
    indexer.save_index(output_path)

    print(f"\n=== 통계 ===")
    print(f"총 프로젝트: {len(projects)}")

    # 카테고리별 통계
    categories = {}
    for p in projects:
        categories[p.category] = categories.get(p.category, 0) + 1

    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}개")
