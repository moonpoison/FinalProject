# 자동화 프로젝트 지식베이스 가이드

## 개요

458개 자동화 프로젝트(1,206개 Python 파일)를 지식베이스로 구축하여 AI 워크플로우 생성 시 참고자료로 활용합니다.

## 시스템 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    지식베이스 시스템                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Indexer   │───▶│  Embedding  │───▶│  ChromaDB   │     │
│  │ (코드 분석) │    │  (벡터화)   │    │ (벡터 저장) │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                                    │              │
│         ▼                                    ▼              │
│  ┌─────────────┐                      ┌─────────────┐      │
│  │   키워드    │──────────┬──────────▶│  Hybrid     │      │
│  │   인덱스    │          │           │  Search     │      │
│  └─────────────┘          │           └─────────────┘      │
│                           │                  │              │
│                           └──────────────────┼──────────────│
│                                              ▼              │
│                                       ┌─────────────┐      │
│                                       │  AI Context │      │
│                                       │  Generator  │      │
│                                       └─────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 설치

```bash
cd backend
pip install chromadb openai
```

## 인덱스 구축

### 방법 1: CLI 스크립트

```bash
cd backend

# 인덱스 구축
python build_knowledge_base.py

# 강제 재구축
python build_knowledge_base.py --force

# 검색 테스트
python build_knowledge_base.py search "네이버 카페 크롤링"

# AI 컨텍스트 생성
python build_knowledge_base.py context "쿠팡 가격 수집"

# 통계 확인
python build_knowledge_base.py stats
```

### 방법 2: API 호출

```bash
# 인덱스 구축 (백그라운드)
curl -X POST http://localhost:8000/api/knowledge/build \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## API 엔드포인트

| 메소드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/knowledge/stats` | 지식베이스 통계 |
| POST | `/api/knowledge/search` | 프로젝트 검색 |
| POST | `/api/knowledge/context` | AI 컨텍스트 생성 |
| GET | `/api/knowledge/project/{id}` | 프로젝트 상세 |
| GET | `/api/knowledge/categories` | 카테고리 목록 |
| GET | `/api/knowledge/selectors/{site}` | 사이트별 셀렉터 |
| POST | `/api/knowledge/build` | 인덱스 구축 |

## 검색 예시

### 요청
```json
POST /api/knowledge/search
{
  "query": "네이버 카페 자동 글쓰기",
  "top_k": 5
}
```

### 응답
```json
{
  "success": true,
  "count": 5,
  "results": [
    {
      "id": "proj_12345",
      "name": "네이버 카페 requests 예약 + 삭제 + 고도화",
      "category": "naver",
      "subcategory": "업로드",
      "sites": ["naver"],
      "libraries": ["selenium", "requests"],
      "description": "네이버 카페 자동 글쓰기. selenium, requests 사용.",
      "score": 0.92,
      "keyword_score": 0.85,
      "semantic_score": 0.95
    }
  ]
}
```

## AI 워크플로우 생성 연동

AI가 워크플로우를 생성할 때 자동으로 지식베이스를 검색하여 유사한 프로젝트를 참고합니다.

### 동작 흐름

1. 사용자가 "네이버 뉴스 크롤링해줘" 요청
2. 지식베이스에서 유사 프로젝트 검색
3. 검색 결과를 Claude 프롬프트에 포함
4. Claude가 기존 프로젝트의 셀렉터, 코드 패턴 참고
5. 더 정확한 워크플로우 생성

### 제공되는 컨텍스트

```
[참고할 수 있는 기존 자동화 프로젝트]

--- 프로젝트 1: 네이버 뉴스 크롤링 (유사도: 95%) ---
카테고리: naver / 크롤링
대상 사이트: naver
사용 라이브러리: selenium, requests
수행 작업: extract, login
주요 셀렉터: .news_tit, .news_dsc, #newsSearchInput

코드 샘플:
```python
def crawl_news(self):
    self.driver.get("https://news.naver.com")
    articles = self.driver.find_elements(By.CSS_SELECTOR, ".news_area")
    ...
```
```

## 카테고리 분류

| 카테고리 | 설명 | 예상 프로젝트 수 |
|----------|------|-----------------|
| naver | 네이버 관련 | 120+ |
| instagram | 인스타그램 | 20+ |
| coupang | 쿠팡 | 10+ |
| carrot | 당근마켓 | 15+ |
| dcinside | 디시인사이드 | 15+ |
| youtube | 유튜브 | 10+ |
| ... | 기타 | ... |

## 하이브리드 검색 알고리즘

```
최종 점수 = 시맨틱 점수 × 0.6 + 키워드 점수 × 0.4

키워드 점수:
- 프로젝트 이름 매칭: ×3.0
- 카테고리 매칭: ×2.5
- 사이트 매칭: ×2.0
- 액션 매칭: ×1.5
- 라이브러리 매칭: ×1.0

시맨틱 점수:
- OpenAI 임베딩 (text-embedding-3-small)
- ChromaDB 벡터 유사도
```

## 환경 변수

```env
# .env 파일
OPENAI_API_KEY=sk-...          # 임베딩용 (없으면 폴백 사용)
AUTOMATION_PROJECTS_PATH=C:\Users\user\Desktop\프로그램 파일
KNOWLEDGE_BASE_DATA_DIR=knowledge_base_data
```

## 파일 구조

```
backend/
├── app/
│   ├── api/
│   │   └── knowledge.py          # API 엔드포인트
│   └── services/
│       └── knowledge_base/
│           ├── __init__.py
│           ├── indexer.py        # 코드 분석기
│           ├── embeddings.py     # 임베딩 서비스
│           ├── search.py         # 하이브리드 검색
│           └── knowledge_base.py # 통합 서비스
├── build_knowledge_base.py       # CLI 스크립트
└── knowledge_base_data/          # 생성되는 데이터
    ├── projects_index.json       # 프로젝트 인덱스
    └── chroma_db/                # 벡터 DB
```

## 주의사항

1. **첫 빌드 시간**: 458개 프로젝트 분석에 약 5-10분 소요
2. **OpenAI API 비용**: 임베딩 생성 시 소량의 API 비용 발생
3. **디스크 공간**: 벡터 DB에 약 100-500MB 필요
4. **메모리**: 빌드 시 약 2-4GB RAM 사용

## 문제 해결

### 인덱스 빌드 실패
```bash
# 캐시 삭제 후 재시도
rm -rf knowledge_base_data/
python build_knowledge_base.py --force
```

### ChromaDB 오류
```bash
pip install --upgrade chromadb
```

### OpenAI API 오류
- API 키 확인
- 없으면 폴백 임베딩 사용 (정확도 낮음)
