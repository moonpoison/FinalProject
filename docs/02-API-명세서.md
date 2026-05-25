# AutoFlow API 명세서

## 기본 정보

- **Base URL**: `http://localhost:8000/api`
- **인증 방식**: Bearer Token (JWT)
- **Content-Type**: `application/json`

---

## 1. 인증 API (`/api/auth`)

### 1.1 회원가입
```http
POST /api/auth/signup
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "홍길동",
  "role": "buyer"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "홍길동",
    "role": "buyer",
    "avatar": null,
    "joined_at": "2024-03-29T00:00:00Z"
  }
}
```

### 1.2 로그인
```http
POST /api/auth/login
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (200):** 회원가입과 동일

### 1.3 현재 사용자 정보
```http
GET /api/auth/me
Authorization: Bearer {token}
```

**Response (200):** UserResponse 객체

### 1.4 로그아웃
```http
POST /api/auth/logout
Authorization: Bearer {token}
```

---

## 2. 채팅 API (`/api/conversations`)

### 2.1 대화 목록 조회
```http
GET /api/conversations
Authorization: Bearer {token}
```

**Response (200):**
```json
[
  {
    "id": "conv-uuid",
    "participant_ids": ["user1", "user2"],
    "participant_names": ["김판매자", "이구매자"],
    "topic": "네이버 자동화 문의",
    "messages": [...],
    "updated_at": "2024-03-29T10:00:00Z"
  }
]
```

### 2.2 대화 생성
```http
POST /api/conversations
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "other_name": "판매자이름",
  "topic": "상품 문의"
}
```

### 2.3 메시지 전송
```http
POST /api/conversations/{conversation_id}/messages
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "body": "안녕하세요!"
}
```

### 2.4 읽음 처리
```http
POST /api/conversations/{conversation_id}/read
Authorization: Bearer {token}
```

### 2.5 읽지 않은 메시지 수
```http
GET /api/conversations/unread-count
Authorization: Bearer {token}
```

---

## 3. 마켓플레이스 API (`/api/marketplace`)

### 3.1 아이템 목록 조회
```http
GET /api/marketplace/items?category=웹자동화&search=네이버&sort=인기순
```

**Query Parameters:**
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| category | string | 카테고리 필터 (전체/웹 자동화/데이터 수집/...) |
| search | string | 검색어 |
| sort | string | 정렬 (인기순/최신순/평점순/무료) |
| skip | int | 페이지네이션 offset |
| limit | int | 페이지네이션 limit |

**Response (200):**
```json
{
  "items": [
    {
      "id": "item-uuid",
      "title": "네이버 쇼핑 최저가 수집기",
      "description": "...",
      "category": "데이터 수집",
      "price": 9900,
      "rating": 4.8,
      "reviews": 342,
      "downloads": 2841,
      "creator": "자동화마스터",
      "tags": ["네이버", "쇼핑"],
      "block_colors": ["#22c55e", "#3b82f6"],
      "featured": true,
      "verified": true
    }
  ],
  "total": 100
}
```

### 3.2 아이템 상세 조회
```http
GET /api/marketplace/items/{item_id}
```

### 3.3 아이템 등록
```http
POST /api/marketplace/items
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "title": "자동화 제목",
  "description": "설명",
  "category": "웹 자동화",
  "price": 9900,
  "tags": ["태그1", "태그2"],
  "blocks_data": [...],
  "block_colors": ["#22c55e"]
}
```

### 3.4 아이템 수정
```http
PUT /api/marketplace/items/{item_id}
Authorization: Bearer {token}
```

### 3.5 아이템 삭제
```http
DELETE /api/marketplace/items/{item_id}
Authorization: Bearer {token}
```

### 3.6 리뷰 목록 조회
```http
GET /api/marketplace/items/{item_id}/reviews
```

### 3.7 리뷰 작성
```http
POST /api/marketplace/items/{item_id}/reviews
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "rating": 5,
  "text": "정말 유용한 자동화입니다!"
}
```

---

## 4. 구매 API (`/api/purchases`)

### 4.1 구매 목록 조회
```http
GET /api/purchases
Authorization: Bearer {token}
```

**Response (200):**
```json
{
  "active": [...],
  "pending": [...],
  "cancelled": [...]
}
```

### 4.2 구매하기
```http
POST /api/purchases
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "item_id": "item-uuid"
}
```

### 4.3 구매 확정
```http
POST /api/purchases/{purchase_id}/confirm
Authorization: Bearer {token}
```

### 4.4 구매 취소
```http
POST /api/purchases/{purchase_id}/cancel
Authorization: Bearer {token}
```

---

## 5. 사용자 API (`/api/users`)

### 5.1 내 정보 조회
```http
GET /api/users/me
Authorization: Bearer {token}
```

### 5.2 내 정보 수정
```http
PUT /api/users/me
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "name": "새이름",
  "avatar": "url"
}
```

### 5.3 내 템플릿 목록
```http
GET /api/users/me/templates
Authorization: Bearer {token}
```

### 5.4 템플릿 생성
```http
POST /api/users/me/templates
Authorization: Bearer {token}
```

### 5.5 템플릿 수정
```http
PUT /api/users/me/templates/{template_id}
Authorization: Bearer {token}
```

### 5.6 템플릿 삭제
```http
DELETE /api/users/me/templates/{template_id}
Authorization: Bearer {token}
```

### 5.7 내 통계 조회
```http
GET /api/users/me/stats
Authorization: Bearer {token}
```

---

## 6. AI API (`/api/ai`)

### 6.1 프롬프트 분석
```http
POST /api/ai/analyze
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "prompt": "네이버 뉴스에서 오늘의 인기 기사 10개를 수집해서 엑셀로 저장해줘"
}
```

**Response (200):**
```json
{
  "task_name": "네이버 뉴스 수집",
  "summary": "네이버 뉴스에서 인기 기사를 수집하여 엑셀로 저장합니다.",
  "confidence": 87,
  "groups": [
    {
      "id": "g1",
      "label": "사이트 접속",
      "description": "네이버 뉴스 페이지에 접속합니다.",
      "color": "#22c55e",
      "steps": [
        {
          "id": "s1",
          "label": "시작하기",
          "description": "워크플로우를 시작합니다.",
          "block_type": "start",
          "color": "#22c55e"
        }
      ]
    }
  ]
}
```

### 6.2 블록 생성
```http
POST /api/ai/generate-blocks
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "groups": [...] // AIAnalyzeResponse의 groups
}
```

**Response (200):**
```json
{
  "blocks": [
    {
      "id": "start",
      "type": "start",
      "category": "start",
      "label": "시작하기",
      "icon": "play",
      "color": "#22c55e",
      "fields": [],
      "instance_id": "start-1711700000000",
      "field_values": {},
      "group_id": "g1",
      "group_label": "사이트 접속",
      "group_color": "#22c55e"
    }
  ]
}
```

---

## 에러 응답

모든 API는 다음 형식의 에러 응답을 반환합니다:

```json
{
  "detail": "에러 메시지"
}
```

### HTTP 상태 코드
| 코드 | 설명 |
|------|------|
| 200 | 성공 |
| 201 | 생성됨 |
| 400 | 잘못된 요청 |
| 401 | 인증 필요 |
| 403 | 권한 없음 |
| 404 | 리소스 없음 |
| 500 | 서버 에러 |
