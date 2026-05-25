"""
Hybrid Search - 키워드 + 벡터 검색 통합
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SearchResult:
    """검색 결과"""
    id: str
    name: str
    category: str
    subcategory: str
    sites: List[str]
    libraries: List[str]
    description: str
    path: str
    score: float  # 통합 점수 (0~1)
    keyword_score: float
    semantic_score: float
    matched_keywords: List[str]


class HybridSearch:
    """하이브리드 검색 (키워드 + 시맨틱)"""

    # 키워드 가중치
    KEYWORD_WEIGHTS = {
        "name": 3.0,      # 프로젝트 이름 매칭
        "category": 2.5,  # 카테고리 매칭
        "sites": 2.0,     # 사이트 매칭
        "actions": 1.5,   # 액션 매칭
        "libraries": 1.0  # 라이브러리 매칭
    }

    # 시맨틱 vs 키워드 비율 (0.6 = 시맨틱 60%, 키워드 40%)
    SEMANTIC_WEIGHT = 0.6

    # 동의어/유사어 매핑 (검색 확장용)
    SYNONYMS = {
        # 카카오 관련
        "카톡": ["카카오톡", "카카오", "톡톡", "오픈톡", "채팅", "메신저", "kakao", "kakaotalk", "opentalk"],
        "카카오톡": ["카톡", "카카오", "톡톡", "오픈톡", "채팅", "kakao", "kakaotalk"],
        "오픈톡": ["카톡", "카카오톡", "톡톡", "오픈채팅", "오픈카톡"],
        "톡톡": ["카톡", "카카오톡", "오픈톡", "채팅"],
        # 네이버 관련
        "네이버": ["naver", "네이버카페", "카페", "블로그", "밴드"],
        "카페": ["cafe", "네이버카페", "다음카페", "커뮤니티"],
        "블로그": ["blog", "네이버블로그", "티스토리", "포스팅"],
        # 작업 유형
        "크롤링": ["크롤러", "수집", "스크래핑", "scraping", "crawling", "추출", "파싱"],
        "글쓰기": ["글작성", "작성", "등록", "업로드", "포스팅", "글등록", "게시", "발행"],
        "매크로": ["자동화", "봇", "bot", "automation", "자동", "반복"],
        "로그인": ["login", "인증", "signin", "로그", "접속"],
        "댓글": ["comment", "답글", "리플", "코멘트", "대댓글"],
        "메시지": ["message", "쪽지", "dm", "채팅", "톡", "문자"],
        # 플랫폼
        "인스타": ["인스타그램", "instagram", "ig", "insta"],
        "유튜브": ["youtube", "yt", "유투브"],
        "쿠팡": ["coupang", "쇼핑", "이커머스"],
        "지마켓": ["gmarket", "g마켓", "옥션"],
        "11번가": ["11st", "십일번가"],
        "당근": ["당근마켓", "daangn", "carrot", "중고"],
        "번개": ["번개장터", "bunjang", "번장"],
        "디스코드": ["discord", "디코"],
        "텔레그램": ["telegram", "텔레", "tg"],
    }

    def __init__(self, projects: List[Dict[str, Any]]):
        self.projects = {p["id"]: p for p in projects}
        self._build_keyword_index()

    def _build_keyword_index(self):
        """키워드 인덱스 구축"""
        self.keyword_index = {
            "name": {},
            "category": {},
            "sites": {},
            "actions": {},
            "libraries": {}
        }

        for proj_id, proj in self.projects.items():
            # 이름 토큰화
            name_tokens = self._tokenize(proj.get("name", ""))
            for token in name_tokens:
                self.keyword_index["name"].setdefault(token, []).append(proj_id)

            # 카테고리
            cat = proj.get("category", "").lower()
            self.keyword_index["category"].setdefault(cat, []).append(proj_id)

            subcat = proj.get("subcategory", "").lower()
            self.keyword_index["category"].setdefault(subcat, []).append(proj_id)

            # 사이트
            for site in proj.get("sites", []):
                self.keyword_index["sites"].setdefault(site.lower(), []).append(proj_id)

            # 액션
            for action in proj.get("actions", []):
                self.keyword_index["actions"].setdefault(action.lower(), []).append(proj_id)

            # 라이브러리
            for lib in proj.get("libraries", []):
                self.keyword_index["libraries"].setdefault(lib.lower(), []).append(proj_id)

    def _tokenize(self, text: str) -> List[str]:
        """텍스트 토큰화"""
        # 한글, 영문, 숫자 분리
        tokens = re.findall(r'[가-힣]+|[a-zA-Z]+|[0-9]+', text.lower())
        return [t for t in tokens if len(t) > 1]

    def _expand_with_synonyms(self, tokens: List[str]) -> List[str]:
        """토큰을 동의어로 확장"""
        expanded = set(tokens)
        for token in tokens:
            # 동의어 추가
            if token in self.SYNONYMS:
                expanded.update(self.SYNONYMS[token])
            # 역방향도 체크 (동의어에서 원본 키워드 찾기)
            for key, synonyms in self.SYNONYMS.items():
                if token in synonyms:
                    expanded.add(key)
                    expanded.update(synonyms)
        return list(expanded)

    def keyword_search(self, query: str, limit: int = 20) -> List[Tuple[str, float, List[str]]]:
        """키워드 기반 검색 (동의어 확장 포함)"""
        query_tokens = self._tokenize(query)
        # 동의어로 확장
        expanded_tokens = self._expand_with_synonyms(query_tokens)
        print(f"[KB] 검색어 확장: {query_tokens} -> {expanded_tokens[:10]}...")
        scores = {}  # proj_id -> (score, matched_keywords)

        for token in expanded_tokens:
            for field, weight in self.KEYWORD_WEIGHTS.items():
                index = self.keyword_index.get(field, {})

                # 정확 매칭
                if token in index:
                    for proj_id in index[token]:
                        if proj_id not in scores:
                            scores[proj_id] = [0.0, []]
                        scores[proj_id][0] += weight
                        scores[proj_id][1].append(f"{field}:{token}")

                # 부분 매칭
                for key, proj_ids in index.items():
                    if token in key or key in token:
                        for proj_id in proj_ids:
                            if proj_id not in scores:
                                scores[proj_id] = [0.0, []]
                            scores[proj_id][0] += weight * 0.5  # 부분 매칭은 50%
                            if f"{field}:{key}" not in scores[proj_id][1]:
                                scores[proj_id][1].append(f"{field}:{key}")

        # 점수 정규화 (0~1)
        if scores:
            max_score = max(s[0] for s in scores.values())
            for proj_id in scores:
                scores[proj_id][0] /= max_score if max_score > 0 else 1

        # 정렬 및 반환
        sorted_results = sorted(scores.items(), key=lambda x: -x[1][0])[:limit]
        return [(proj_id, score, keywords) for proj_id, (score, keywords) in sorted_results]

    def hybrid_search(self, query: str, semantic_results: List[Dict[str, Any]],
                     top_k: int = 5) -> List[SearchResult]:
        """하이브리드 검색 (키워드 + 시맨틱 통합)"""
        # 1. 키워드 검색
        keyword_results = self.keyword_search(query, limit=top_k * 2)
        keyword_scores = {proj_id: (score, keywords) for proj_id, score, keywords in keyword_results}

        # 2. 시맨틱 검색 결과 정규화
        semantic_scores = {}
        for result in semantic_results:
            proj_id = result["id"]
            similarity = result.get("similarity", 0)
            semantic_scores[proj_id] = similarity

        # 3. 통합 점수 계산
        all_ids = set(keyword_scores.keys()) | set(semantic_scores.keys())
        combined_results = []

        for proj_id in all_ids:
            kw_score, matched = keyword_scores.get(proj_id, (0.0, []))
            sem_score = semantic_scores.get(proj_id, 0.0)

            # 가중 평균
            combined_score = (
                self.SEMANTIC_WEIGHT * sem_score +
                (1 - self.SEMANTIC_WEIGHT) * kw_score
            )

            proj = self.projects.get(proj_id)
            if proj:
                combined_results.append(SearchResult(
                    id=proj_id,
                    name=proj.get("name", ""),
                    category=proj.get("category", ""),
                    subcategory=proj.get("subcategory", ""),
                    sites=proj.get("sites", []),
                    libraries=proj.get("libraries", []),
                    description=proj.get("description", ""),
                    path=proj.get("path", ""),
                    score=combined_score,
                    keyword_score=kw_score,
                    semantic_score=sem_score,
                    matched_keywords=matched
                ))

        # 점수순 정렬
        combined_results.sort(key=lambda x: -x.score)

        return combined_results[:top_k]

    def search_by_category(self, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """카테고리별 검색"""
        results = []
        category_lower = category.lower()

        for proj in self.projects.values():
            if (proj.get("category", "").lower() == category_lower or
                category_lower in proj.get("sites", [])):
                results.append(proj)

        return results[:limit]

    def search_by_site(self, site: str, limit: int = 10) -> List[Dict[str, Any]]:
        """사이트별 검색"""
        results = []
        site_lower = site.lower()

        for proj in self.projects.values():
            if site_lower in [s.lower() for s in proj.get("sites", [])]:
                results.append(proj)

        return results[:limit]

    def get_similar_projects(self, project_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """유사 프로젝트 찾기"""
        target = self.projects.get(project_id)
        if not target:
            return []

        scores = {}

        for proj_id, proj in self.projects.items():
            if proj_id == project_id:
                continue

            score = 0

            # 같은 카테고리
            if proj.get("category") == target.get("category"):
                score += 2

            # 같은 서브카테고리
            if proj.get("subcategory") == target.get("subcategory"):
                score += 1

            # 사이트 겹침
            common_sites = set(proj.get("sites", [])) & set(target.get("sites", []))
            score += len(common_sites) * 1.5

            # 라이브러리 겹침
            common_libs = set(proj.get("libraries", [])) & set(target.get("libraries", []))
            score += len(common_libs) * 0.5

            # 액션 겹침
            common_actions = set(proj.get("actions", [])) & set(target.get("actions", []))
            score += len(common_actions) * 0.5

            if score > 0:
                scores[proj_id] = score

        # 정렬
        sorted_ids = sorted(scores.items(), key=lambda x: -x[1])[:limit]

        return [self.projects[proj_id] for proj_id, _ in sorted_ids]


# CLI 테스트
if __name__ == "__main__":
    # 테스트 데이터
    test_projects = [
        {
            "id": "p1",
            "name": "네이버 카페 크롤링",
            "category": "naver",
            "subcategory": "크롤링",
            "sites": ["naver"],
            "actions": ["extract", "login"],
            "libraries": ["selenium", "requests"],
            "description": "네이버 카페 글 수집",
            "path": "/test/p1"
        },
        {
            "id": "p2",
            "name": "쿠팡 가격 추출",
            "category": "coupang",
            "subcategory": "크롤링",
            "sites": ["coupang"],
            "actions": ["extract"],
            "libraries": ["requests", "beautifulsoup4"],
            "description": "쿠팡 상품 가격 크롤링",
            "path": "/test/p2"
        },
    ]

    search = HybridSearch(test_projects)

    # 키워드 검색 테스트
    results = search.keyword_search("네이버 크롤링")
    print("키워드 검색 결과:")
    for proj_id, score, keywords in results:
        print(f"  {proj_id}: {score:.2f} - {keywords}")
