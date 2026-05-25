"""
Embedding Service - 코드를 벡터 임베딩으로 변환
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False


class EmbeddingService:
    """OpenAI 임베딩 서비스"""

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.cache_dir = Path("embedding_cache")
        self.cache_dir.mkdir(exist_ok=True)

        if HAS_OPENAI and self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None
            print("[Embedding] OpenAI 클라이언트 초기화 실패 - API 키 확인 필요")

    def _get_cache_key(self, text: str) -> str:
        """텍스트의 캐시 키 생성"""
        return hashlib.md5(text.encode()).hexdigest()

    def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """캐시된 임베딩 가져오기"""
        cache_key = self._get_cache_key(text)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return None

    def _cache_embedding(self, text: str, embedding: List[float]):
        """임베딩 캐시 저장"""
        cache_key = self._get_cache_key(text)
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            with open(cache_file, 'w') as f:
                json.dump(embedding, f)
        except:
            pass

    def embed_text(self, text: str) -> List[float]:
        """단일 텍스트 임베딩"""
        if not text.strip():
            return [0.0] * 1536  # 기본 차원

        # 캐시 확인
        cached = self._get_cached_embedding(text)
        if cached:
            return cached

        if not self.client:
            # OpenAI 없으면 간단한 해시 기반 벡터 생성 (테스트용)
            return self._fallback_embedding(text)

        try:
            # 텍스트 길이 제한 (8191 토큰)
            truncated = text[:30000]  # 약 8000 토큰

            response = self.client.embeddings.create(
                model=self.model,
                input=truncated
            )
            embedding = response.data[0].embedding

            # 캐시 저장
            self._cache_embedding(text, embedding)

            return embedding
        except Exception as e:
            print(f"[Embedding] 오류: {e}")
            return self._fallback_embedding(text)

    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """배치 임베딩"""
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            print(f"  [Embedding] 배치 {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}")

            for text in batch:
                embedding = self.embed_text(text)
                embeddings.append(embedding)

        return embeddings

    def _fallback_embedding(self, text: str) -> List[float]:
        """OpenAI 없을 때 폴백 임베딩 (간단한 해시 기반)"""
        import hashlib

        # 텍스트를 해시로 변환 후 벡터화
        hash_bytes = hashlib.sha512(text.encode()).digest()

        # 1536 차원으로 확장 (반복)
        vector = []
        for i in range(1536):
            byte_idx = i % len(hash_bytes)
            # -1 ~ 1 범위로 정규화
            value = (hash_bytes[byte_idx] / 127.5) - 1
            vector.append(value)

        return vector

    def embed_code_project(self, project: Dict[str, Any]) -> List[float]:
        """프로젝트 전체를 임베딩"""
        # 임베딩할 텍스트 조합
        parts = [
            f"프로젝트: {project.get('name', '')}",
            f"설명: {project.get('description', '')}",
            f"카테고리: {project.get('category', '')} / {project.get('subcategory', '')}",
            f"사이트: {', '.join(project.get('sites', []))}",
            f"라이브러리: {', '.join(project.get('libraries', []))}",
            f"액션: {', '.join(project.get('actions', []))}",
            "",
            "코드 샘플:",
            project.get('main_code', '')[:2000]
        ]

        combined_text = "\n".join(parts)
        return self.embed_text(combined_text)


class ChromaDBStore:
    """ChromaDB 벡터 저장소"""

    def __init__(self, persist_dir: str = "chroma_db"):
        if not HAS_CHROMADB:
            raise ImportError("chromadb가 설치되지 않았습니다: pip install chromadb")

        self.persist_dir = persist_dir
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="automation_projects",
            metadata={"description": "자동화 프로젝트 지식베이스"}
        )
        print(f"[ChromaDB] 초기화 완료: {persist_dir}")

    def add_projects(self, projects: List[Dict[str, Any]], embeddings: List[List[float]]):
        """프로젝트들을 DB에 추가"""
        ids = [p["id"] for p in projects]
        documents = [self._project_to_document(p) for p in projects]
        metadatas = [self._project_to_metadata(p) for p in projects]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        print(f"[ChromaDB] {len(projects)}개 프로젝트 추가 완료")

    def _project_to_document(self, project: Dict[str, Any]) -> str:
        """프로젝트를 검색 가능한 문서로 변환"""
        return f"""
프로젝트: {project.get('name', '')}
설명: {project.get('description', '')}
카테고리: {project.get('category', '')} / {project.get('subcategory', '')}
사이트: {', '.join(project.get('sites', []))}
라이브러리: {', '.join(project.get('libraries', []))}
액션: {', '.join(project.get('actions', []))}
셀렉터: {', '.join(project.get('selectors', [])[:5])}
"""

    def _project_to_metadata(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """프로젝트 메타데이터"""
        return {
            "name": project.get("name", ""),
            "category": project.get("category", ""),
            "subcategory": project.get("subcategory", ""),
            "sites": ",".join(project.get("sites", [])),
            "libraries": ",".join(project.get("libraries", [])),
            "path": project.get("path", ""),
        }

    def search(self, query_embedding: List[float], n_results: int = 5,
               category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """벡터 검색"""
        where_filter = None
        if category_filter:
            where_filter = {"category": category_filter}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        # 결과 포맷팅
        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
                "similarity": 1 - results["distances"][0][i]  # 유사도로 변환
            })

        return formatted

    def search_by_text(self, query: str, embedding_service: EmbeddingService,
                       n_results: int = 5) -> List[Dict[str, Any]]:
        """텍스트로 검색 (임베딩 자동 생성)"""
        query_embedding = embedding_service.embed_text(query)
        return self.search(query_embedding, n_results)

    def get_stats(self) -> Dict[str, Any]:
        """DB 통계"""
        return {
            "total_projects": self.collection.count(),
            "persist_dir": self.persist_dir
        }


# CLI 실행
if __name__ == "__main__":
    print("=== Embedding Service Test ===")

    service = EmbeddingService()

    # 테스트 텍스트
    test_text = "네이버 카페 자동 글쓰기 매크로. Selenium과 requests를 사용하여 로그인 후 글을 등록합니다."
    embedding = service.embed_text(test_text)

    print(f"텍스트: {test_text}")
    print(f"임베딩 차원: {len(embedding)}")
    print(f"처음 5개 값: {embedding[:5]}")
