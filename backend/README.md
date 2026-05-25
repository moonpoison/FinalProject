# AutoFlow Backend

AI 기반 업무 자동화 플랫폼 AutoFlow의 백엔드 API 서버입니다.

## 기술 스택

- **Framework**: FastAPI
- **Database**: SQLite + SQLAlchemy (Async)
- **Authentication**: JWT
- **AI**: Anthropic Claude API

## 빠른 시작

### 1. 의존성 설치

```bash
# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 ANTHROPIC_API_KEY 설정
```

### 3. 서버 실행

```bash
python run.py
```

서버가 `http://localhost:8000`에서 실행됩니다.

## API 문서

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 데모 계정

서버 시작 시 자동으로 생성되는 데모 계정:

| 이메일 | 비밀번호 | 역할 |
|--------|----------|------|
| seller@demo.com | demo1234 | 판매자 |
| buyer@demo.com | demo1234 | 구매자 |

## API 엔드포인트

### 인증 (`/api/auth`)
- `POST /signup` - 회원가입
- `POST /login` - 로그인
- `GET /me` - 현재 사용자 정보
- `POST /logout` - 로그아웃

### 채팅 (`/api/conversations`)
- `GET /` - 대화 목록
- `POST /` - 대화 생성
- `POST /{id}/messages` - 메시지 전송
- `POST /{id}/read` - 읽음 처리

### 마켓플레이스 (`/api/marketplace`)
- `GET /items` - 아이템 목록
- `GET /items/{id}` - 아이템 상세
- `POST /items` - 아이템 등록
- `PUT /items/{id}` - 아이템 수정
- `DELETE /items/{id}` - 아이템 삭제

### 구매 (`/api/purchases`)
- `GET /` - 구매 목록
- `POST /` - 구매
- `POST /{id}/confirm` - 구매 확정
- `POST /{id}/cancel` - 구매 취소

### AI (`/api/ai`)
- `POST /analyze` - 프롬프트 분석
- `POST /generate-blocks` - 블록 생성

## 프로젝트 구조

```
backend/
├── app/
│   ├── main.py          # FastAPI 앱
│   ├── config.py        # 설정
│   ├── database.py      # DB 연결
│   ├── models/          # SQLAlchemy 모델
│   ├── schemas/         # Pydantic 스키마
│   ├── api/             # API 라우터
│   └── utils/           # 유틸리티
├── requirements.txt
├── run.py
└── .env.example
```

## 라이선스

MIT License
