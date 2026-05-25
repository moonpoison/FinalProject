"""
Knowledge Base - 자동화 프로젝트 지식베이스 통합 서비스
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from .indexer import CodeIndexer, AutomationProject
from .embeddings import EmbeddingService, ChromaDBStore
from .search import HybridSearch, SearchResult


class KnowledgeBase:
    """자동화 프로젝트 지식베이스"""

    def __init__(
        self,
        projects_path: str = r"C:\Users\user\Desktop\프로그램 파일",
        data_dir: str = "knowledge_base_data",
        openai_api_key: Optional[str] = None
    ):
        self.projects_path = Path(projects_path)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.index_file = self.data_dir / "projects_index.json"
        self.chroma_dir = str(self.data_dir / "chroma_db")

        # 서비스 초기화
        self.embedding_service = EmbeddingService(api_key=openai_api_key)
        self.indexer = CodeIndexer(str(self.projects_path))

        # 프로젝트 로드
        self.projects: List[Dict[str, Any]] = []
        self.hybrid_search: Optional[HybridSearch] = None
        self.chroma_store: Optional[ChromaDBStore] = None

        self._load_or_build()

    def _load_or_build(self):
        """기존 인덱스 로드 또는 새로 빌드"""
        if self.index_file.exists():
            print("[KB] 기존 인덱스 로드 중...")
            self._load_index()
        else:
            print("[KB] 인덱스가 없습니다. build_index()를 실행하세요.")

    def _load_index(self):
        """인덱스 로드"""
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.projects = json.load(f)

            self.hybrid_search = HybridSearch(self.projects)

            # ChromaDB 로드 시도
            try:
                self.chroma_store = ChromaDBStore(self.chroma_dir)
                stats = self.chroma_store.get_stats()
                print(f"[KB] 로드 완료: {len(self.projects)}개 프로젝트, ChromaDB: {stats['total_projects']}개")
            except Exception as e:
                print(f"[KB] ChromaDB 로드 실패: {e}")
                self.chroma_store = None

        except Exception as e:
            print(f"[KB] 인덱스 로드 실패: {e}")

    def build_index(self, force: bool = False):
        """인덱스 구축"""
        if self.index_file.exists() and not force:
            print("[KB] 인덱스가 이미 존재합니다. force=True로 재구축하세요.")
            return

        print("[KB] === 인덱스 구축 시작 ===")

        # 1. 프로젝트 스캔
        print("\n[1/3] 프로젝트 스캔 중...")
        indexed_projects = self.indexer.scan_all_projects()
        self.projects = [asdict(p) for p in indexed_projects]

        # 2. 인덱스 저장
        print("\n[2/3] 인덱스 저장 중...")
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.projects, f, ensure_ascii=False, indent=2)

        # 3. 임베딩 생성 및 ChromaDB 저장
        print("\n[3/3] 임베딩 생성 및 벡터 DB 저장 중...")
        try:
            self.chroma_store = ChromaDBStore(self.chroma_dir)

            # 배치로 임베딩 생성
            embeddings = []
            for i, proj in enumerate(self.projects):
                if i % 50 == 0:
                    print(f"  임베딩 생성 중: {i}/{len(self.projects)}")
                embedding = self.embedding_service.embed_code_project(proj)
                embeddings.append(embedding)

            # ChromaDB에 저장
            self.chroma_store.add_projects(self.projects, embeddings)

        except Exception as e:
            print(f"[KB] 벡터 DB 구축 실패: {e}")
            self.chroma_store = None

        # 하이브리드 검색 초기화
        self.hybrid_search = HybridSearch(self.projects)

        print(f"\n[KB] === 인덱스 구축 완료 ===")
        print(f"  총 프로젝트: {len(self.projects)}")
        self._print_stats()

    def _print_stats(self):
        """통계 출력"""
        categories = {}
        sites = {}
        libraries = {}

        for proj in self.projects:
            cat = proj.get("category", "기타")
            categories[cat] = categories.get(cat, 0) + 1

            for site in proj.get("sites", []):
                sites[site] = sites.get(site, 0) + 1

            for lib in proj.get("libraries", []):
                libraries[lib] = libraries.get(lib, 0) + 1

        print("\n  카테고리별:")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:10]:
            print(f"    {cat}: {count}개")

        print("\n  라이브러리별:")
        for lib, count in sorted(libraries.items(), key=lambda x: -x[1])[:5]:
            print(f"    {lib}: {count}개")

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """통합 검색 (하이브리드)"""
        if not self.hybrid_search:
            print("[KB] 인덱스가 로드되지 않았습니다.")
            return []

        # 시맨틱 검색
        semantic_results = []
        if self.chroma_store:
            try:
                semantic_results = self.chroma_store.search_by_text(
                    query, self.embedding_service, n_results=top_k * 2
                )
            except Exception as e:
                print(f"[KB] 시맨틱 검색 오류: {e}")

        # 하이브리드 검색
        results = self.hybrid_search.hybrid_search(query, semantic_results, top_k)

        return results

    def search_for_workflow(self, prompt: str, top_k: int = 5, include_full_code: bool = False) -> Dict[str, Any]:
        """워크플로우 생성을 위한 검색 (AI 컨텍스트용)

        Args:
            prompt: 검색 쿼리
            top_k: 반환할 결과 수
            include_full_code: True면 전체 코드 포함 (더 많은 컨텍스트)
        """
        results = self.search(prompt, top_k)

        if not results:
            return {"found": False, "references": []}

        references = []
        for result in results:
            # 해당 프로젝트의 전체 정보 가져오기
            full_project = next(
                (p for p in self.projects if p["id"] == result.id),
                None
            )

            if full_project:
                # 전체 코드 우선 사용 (사용자 요청: 프로젝트 전체를 참고)
                full_code = full_project.get("full_code", "")
                main_code = full_project.get("main_code", "")

                # include_full_code=True면 전체 코드 사용
                if include_full_code:
                    code_sample = full_code if full_code else main_code
                else:
                    # 기본: main_code 우선, 부족하면 full_code 추가
                    code_sample = main_code if main_code else full_code[:30000]

                # 코드가 너무 짧으면 건너뛰기
                if len(code_sample) < 50:
                    continue

                references.append({
                    "name": result.name,
                    "category": result.category,
                    "subcategory": result.subcategory,
                    "sites": result.sites,
                    "libraries": result.libraries,
                    "actions": full_project.get("actions", []),
                    "selectors": full_project.get("selectors", []),  # 모든 셀렉터
                    "description": result.description,
                    "similarity": result.score,
                    "code_sample": code_sample,
                    "full_code": full_code,  # 전체 코드도 별도 제공
                    "path": full_project.get("path", "")
                })

        return {
            "found": True,
            "count": len(references),
            "references": references
        }

    def get_context_for_ai(self, prompt: str, max_code_per_project: int = 15000) -> str:
        """AI에게 제공할 컨텍스트 문자열 생성

        Args:
            prompt: 검색 쿼리
            max_code_per_project: 프로젝트당 최대 코드 길이 (기본 15000자)
        """
        # include_full_code=True로 전체 코드 포함
        search_result = self.search_for_workflow(prompt, top_k=3, include_full_code=True)

        if not search_result["found"]:
            return ""

        context_parts = ["""[참고할 수 있는 기존 자동화 프로젝트 - 코드 패턴을 적극 활용하세요]

중요: 아래 코드들은 실제 작동이 검증된 코드입니다.
- CSS 셀렉터는 가능한 그대로 사용하세요
- 로그인, 크롤링 패턴을 참고하세요
- custom-code 블록에서 이 코드들을 활용하세요
"""]

        for i, ref in enumerate(search_result["references"], 1):
            # 전체 코드 사용 (유사도 높은 순으로 더 많은 코드 제공)
            code_to_include = ref.get('full_code', '') or ref.get('code_sample', '')
            code_limit = max_code_per_project if i == 1 else max_code_per_project // 2

            context_parts.append(f"""
======================================
프로젝트 {i}: {ref['name']} (유사도: {ref['similarity']:.0%})
======================================
카테고리: {ref['category']} / {ref['subcategory']}
대상 사이트: {', '.join(ref['sites'])}
사용 라이브러리: {', '.join(ref['libraries'])}
수행 작업: {', '.join(ref['actions'])}
프로젝트 경로: {ref.get('path', '')}

### 주요 CSS 셀렉터 (실제 작동 확인됨):
{chr(10).join(['  - ' + s for s in ref['selectors'][:50]])}

### 전체 코드 (custom-code 블록에서 활용 가능):
```python
{code_to_include[:code_limit]}
```
""")

        return "\n".join(context_parts)

    def get_selectors_for_site(self, site: str) -> List[str]:
        """특정 사이트의 셀렉터 모음 가져오기"""
        all_selectors = []

        for proj in self.projects:
            if site.lower() in [s.lower() for s in proj.get("sites", [])]:
                all_selectors.extend(proj.get("selectors", []))

        # 중복 제거 및 빈도순 정렬
        selector_counts = {}
        for sel in all_selectors:
            selector_counts[sel] = selector_counts.get(sel, 0) + 1

        sorted_selectors = sorted(selector_counts.items(), key=lambda x: -x[1])

        return [sel for sel, _ in sorted_selectors[:30]]

    def get_project_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """ID로 프로젝트 조회"""
        return next((p for p in self.projects if p["id"] == project_id), None)

    def get_projects_by_category(self, category: str) -> List[Dict[str, Any]]:
        """카테고리별 프로젝트 조회"""
        return [p for p in self.projects if p.get("category", "").lower() == category.lower()]

    def get_stats(self) -> Dict[str, Any]:
        """통계 정보"""
        categories = {}
        total_lines = 0

        for proj in self.projects:
            cat = proj.get("category", "기타")
            categories[cat] = categories.get(cat, 0) + 1
            total_lines += proj.get("total_lines", 0)

        return {
            "total_projects": len(self.projects),
            "total_lines": total_lines,
            "categories": categories,
            "has_vector_db": self.chroma_store is not None
        }


# 싱글톤 인스턴스 (앱 전역 사용)
_knowledge_base: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """지식베이스 싱글톤 가져오기"""
    global _knowledge_base

    if _knowledge_base is None:
        # 환경변수에서 경로 가져오기
        projects_path = os.getenv(
            "AUTOMATION_PROJECTS_PATH",
            r"C:\Users\user\Desktop\프로그램 파일"
        )
        data_dir = os.getenv(
            "KNOWLEDGE_BASE_DATA_DIR",
            "knowledge_base_data"
        )

        # settings에서 API 키 가져오기 (서버 환경)
        openai_key = None
        try:
            from app.config import settings
            openai_key = getattr(settings, 'OPENAI_API_KEY', None)
        except:
            pass

        # 환경변수 폴백
        if not openai_key:
            openai_key = os.getenv("OPENAI_API_KEY")

        _knowledge_base = KnowledgeBase(
            projects_path=projects_path,
            data_dir=data_dir,
            openai_api_key=openai_key
        )

    return _knowledge_base


# CLI 실행
if __name__ == "__main__":
    import sys

    kb = KnowledgeBase()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "build":
            kb.build_index(force="--force" in sys.argv)

        elif command == "search":
            query = " ".join(sys.argv[2:])
            results = kb.search(query)
            print(f"\n검색 결과 ({query}):")
            for r in results:
                print(f"  [{r.score:.2f}] {r.name} - {r.category}/{r.subcategory}")
                print(f"       {r.description}")

        elif command == "context":
            query = " ".join(sys.argv[2:])
            context = kb.get_context_for_ai(query)
            print(context)

        elif command == "stats":
            stats = kb.get_stats()
            print(json.dumps(stats, ensure_ascii=False, indent=2))

    else:
        print("사용법:")
        print("  python knowledge_base.py build [--force]  # 인덱스 구축")
        print("  python knowledge_base.py search <쿼리>    # 검색")
        print("  python knowledge_base.py context <쿼리>   # AI 컨텍스트 생성")
        print("  python knowledge_base.py stats            # 통계")
