# 면접 AI 서비스 API

외국인을 위한 한국 취업 면접 준비 AI 서비스 (OpenRouter 기반)

## 주요 기능

### 질문 관리 (Questions)

- 질문 CRUD (공통/직무/외국인특화 카테고리)
- AI 답변 평가 (OpenRouter API 사용)
- QA 히스토리 조회

### 면접 세트 (Interview)

- 면접 세트 생성 (질문 개수 선택 가능)
- 답변 제출 및 AI 꼬리질문 생성
- 면접 완료 및 종합 AI 평가
- 면접 세트 조회 및 목록

### 답변 노트 (Answer Notes)

- 답변 노트 CRUD
- 피드백 저장 및 최종 답변 관리

## 기술 스택

- **FastAPI**: 고성능 웹 프레임워크
- **SQLModel**: SQLAlchemy + Pydantic 통합 ORM
- **SQLite**: 경량 데이터베이스
- **JWT (HMAC512)**: 토큰 기반 인증
- **OpenRouter**: 다양한 AI 모델 통합 API
- **uv**: 빠른 Python 패키지 관리자

## 설치 및 실행

### 1. 프로젝트 설정

```bash
# uv 설치 (없는 경우)
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# uv로 의존성 설치
uv sync
```

### 2. 환경 변수 설정

```bash
# .env 파일 생성
copy .env.example .env
```

`.env` 파일을 열어 다음 값들을 설정하세요:

```env
# 필수 설정
SECRET_KEY=your-secret-key-for-jwt-hs512-change-this-in-production
OPENROUTER_API_KEY=your-openrouter-api-key-here

# 선택적 설정
DEFAULT_AI_MODEL=google/gemini-3-flash-preview
APP_URL=https://your-site-url.com
APP_NAME=면접 AI 서비스

# 초기 데이터 시딩 (ON/OFF)
# True: 앱 시작 시 테스트용 질문 10개 자동 추가
# False: 초기 질문 추가 안 함
SEED_INITIAL_QUESTIONS=True
```

**OpenRouter API 키 발급:**

1. https://openrouter.ai/ 에서 회원가입
2. Settings > Keys 에서 API 키 생성
3. `.env` 파일의 `OPENROUTER_API_KEY`에 복사

### 3. 서버 실행

```bash
# 개발 서버 실행
uv run uvicorn app.main:app --reload

# 또는 Makefile 사용
make dev
```

### 4. API 문서 확인

브라우저에서 다음 주소로 접속:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 초기 데이터 시딩

### 자동 테스트 질문 추가 ⭐

서버를 처음 실행하면 **테스트용 질문 10개**가 자동으로 추가됩니다!

**추가되는 질문:**
- 공통 질문 4개 (자기소개, 지원동기, 강점/약점, 비전)
- IT 직무 질문 3개 (프로그래밍 언어, 기술 충돌, 신기술 학습)
- 외국인특화 질문 3개 (한국어 능력, 문화 적응, 장기 근속)

### ON/OFF 설정

`.env` 파일에서 쉽게 켜고 끌 수 있습니다:

```env
# 초기 질문 추가 활성화 (기본값)
SEED_INITIAL_QUESTIONS=True

# 초기 질문 추가 비활성화
SEED_INITIAL_QUESTIONS=False
```

**작동 방식:**
- 데이터베이스에 질문이 **하나도 없을 때만** 추가됩니다
- 이미 질문이 있으면 추가하지 않습니다
- 서버 시작 시 자동으로 확인하고 추가합니다

**로그 메시지:**
```
[INFO] 초기 테스트 질문 시딩 시작...
[SUCCESS] 10개의 초기 질문이 추가되었습니다.
  - 공통 질문: 4개
  - IT 직무 질문: 3개
  - 외국인특화 질문: 3개
```

또는

```
[INFO] 이미 10개의 질문이 존재합니다. 시딩을 건너뜁니다.
```

> 💡 **Tip**: 테스트 후 데이터를 초기화하려면 `database.db` 파일을 삭제하고 서버를 다시 시작하세요.

## 인증 방법

모든 API는 JWT Bearer Token 인증이 필요합니다.

**알고리즘**: HMAC512 (HS512)

요청 헤더에 `Authorization: Bearer {access_token}` 추가

> 💡 **참고**: 현재 버전은 토큰 발급 기능이 없으며, 외부에서 발급된 JWT 토큰을 검증만 합니다.

## AI 모델 설정

### 기본 모델

기본 AI 모델은 `google/gemini-3-flash-preview`입니다.

### 다른 모델 사용

환경 변수 `DEFAULT_AI_MODEL`을 변경하거나, API 요청 시 `ai_model` 파라미터로 지정할 수 있습니다.

**추천 모델:**

- `google/gemini-flash-1.5` - 빠르고 비용 효율적 (기본값)
- `google/gemini-flash-1.5-8b` - 더 빠르고 저렴
- `anthropic/claude-3.5-sonnet` - 고품질
- `openai/gpt-4o` - 최고 품질
- `google/gemini-2.0-flash-exp:free` - 무료 (제한적)

더 많은 모델: https://openrouter.ai/models

## 데이터베이스 스키마

> 💡 **모든 테이블의 ID는 UUID 형식을 사용합니다.**

### Questions (질문)

- **id**: UUID (Primary Key)
- 공통/직무/외국인특화 카테고리
- 직무 타입 (marketing, sales, it)
- 레벨 (intern, entry)
- 모범답안 및 논리

### Interview Sets (면접 세트)

- **id**: UUID (Primary Key)
- 직무 및 레벨 설정
- 진행 상태 (in_progress, completed)

### Interview Answers (면접 답변)

- **id**: UUID (Primary Key)
- **set_id**: UUID (Foreign Key → interview_sets)
- **question_id**: UUID (Foreign Key → questions)
- 사용자 답변
- AI 생성 꼬리질문 및 답변

### Interview Evaluations (면접 평가)

- **id**: UUID (Primary Key)
- **set_id**: UUID (Foreign Key → interview_sets)
- 5가지 평가 항목 (논리성, 근거, 직무이해도, 한국어 격식, 완성도)
- 종합 피드백 및 상세 피드백

### Answer Notes (답변 노트)

- **id**: UUID (Primary Key)
- **question_id**: UUID (Foreign Key → questions)
- 초기 답변 및 피드백 관리
- 최종 답변 저장

### QA History (QA 히스토리)

- **id**: UUID (Primary Key)
- **question_id**: UUID (Foreign Key → questions)
- 질문별 답변 이력
- AI 모델 및 평가 점수

## API 엔드포인트

> 💡 **모든 경로 파라미터 {id}는 UUID 형식입니다.**

### Questions

- `GET /questions` - 질문 목록
- `POST /questions` - 질문 생성
- `GET /questions/{question_id}` - 질문 조회 (UUID)
- `PUT /questions/{question_id}` - 질문 수정 (UUID)
- `DELETE /questions/{question_id}` - 질문 삭제 (UUID)
- `POST /questions/evaluate` - AI 답변 평가 ✨
- `GET /questions/history/{question_id}` - QA 히스토리 (UUID)

### Interview

- `POST /interview/sets` - 면접 세트 생성
- `GET /interview/sets` - 면접 세트 목록
- `GET /interview/sets/{set_id}` - 면접 세트 조회 (UUID)
- `POST /interview/answers` - 답변 제출 (꼬리질문 생성) ✨
- `POST /interview/follow-up-answers` - 꼬리질문 답변 제출
- `POST /interview/sets/{set_id}/complete` - 면접 완료 및 평가 (UUID) ✨

### Answer Notes

- `GET /answer-notes` - 답변 노트 목록
- `POST /answer-notes` - 답변 노트 생성
- `PUT /answer-notes/{note_id}` - 답변 노트 수정 (UUID)
- `DELETE /answer-notes/{note_id}` - 답변 노트 삭제 (UUID)

✨ = OpenRouter AI 기능 사용

### UUID 형식 예시

```
123e4567-e89b-12d3-a456-426614174000
```

## 테스트

### 빠른 시작 (Windows)

```powershell
# AI 테스트 대화형 실행
.\RUN_AI_TESTS.ps1
```

### 기본 테스트 (API 키 불필요)

```bash
# 모든 기본 테스트 실행
uv run pytest -v

# 특정 테스트 파일 실행
uv run pytest tests/test_questions.py -v
uv run pytest tests/test_interview.py -v
uv run pytest tests/test_answer_notes.py -v

# 커버리지 포함
uv run pytest --cov=app --cov-report=html --cov-report=term
```

### AI 통합 테스트 (API 키 필요) ⭐

**실제 AI 응답을 자세히 볼 수 있는 테스트입니다!**

```bash
# 준비: UTF-8 인코딩 설정 (Windows)
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING="utf-8"
$env:APP_NAME="AI Interview Service"

# 전체 AI 테스트
uv run pytest tests/test_ai_integration.py -v -s

# 개별 테스트
uv run pytest tests/test_ai_integration.py::test_ai_answer_evaluation_detailed -v -s
uv run pytest tests/test_ai_integration.py::test_ai_follow_up_question_generation -v -s
uv run pytest tests/test_ai_integration.py::test_ai_comprehensive_interview_evaluation -v -s
```

**옵션 설명:**

- `-v`: verbose (자세한 출력)
- `-s`: stdout 캡처 안 함 (AI 응답을 실시간으로 볼 수 있음)

### 테스트 주의사항

- **기본 테스트**: API 키 없이 실행 가능, 비용 없음, 빠름 (약 2초)
- **AI 테스트**: OpenRouter API 키 필요, 비용 발생 ($0.005 ~ $0.01), 느림 (약 1분)
- **데이터베이스**: 모든 테스트는 인메모리 SQLite 사용 (실제 DB에 영향 없음)
- **UUID**: 모든 ID는 자동으로 생성되는 UUID 사용

### AI 테스트 예상 비용

| 테스트         | 소요 시간 | 예상 비용 |
| -------------- | --------- | --------- |
| 답변 평가      | 10-15초   | ~$0.001   |
| 꼬리질문 생성  | 15-20초   | ~$0.002   |
| 종합 평가      | 20-30초   | ~$0.003   |
| 전체 AI 테스트 | 50-60초   | ~$0.008   |

## 프로젝트 구조

```
backend-ai/
├── app/
│   ├── api/
│   │   ├── questions.py      # 질문 관리 API
│   │   ├── interview.py      # 면접 세트 API
│   │   └── answer_notes.py   # 답변 노트 API
│   ├── core/
│   │   ├── auth.py           # JWT 인증 (HMAC512)
│   │   ├── config.py         # 환경 설정
│   │   └── database.py       # DB 연결
│   ├── lib/
│   │   └── openrouter.py     # OpenRouter AI 유틸리티
│   ├── models.py             # SQLModel 모델
│   ├── schemas.py            # Pydantic 스키마
│   └── main.py               # FastAPI 앱
├── tests/                    # 테스트
├── .env.example              # 환경 변수 예제
├── pyproject.toml            # 프로젝트 설정
├── Makefile                  # 편의 명령어
└── README.md
```

## OpenRouter 기능

### 구현된 기능

✅ **질문 평가** - 사용자 답변을 모범답안과 비교하여 점수화 및 피드백
✅ **꼬리질문 생성** - 답변 내용을 분석하여 압박 꼬리질문 자동 생성
✅ **종합 평가** - 전체 면접 답변을 5가지 항목으로 종합 평가

### 미구현 기능

⏳ **음성 전사** - OpenRouter는 Whisper API를 직접 지원하지 않음 (OpenAI Whisper API 별도 필요)
⏳ **스트리밍 응답** - 평가 진행 상황을 실시간으로 보여주는 SSE

## 비용 관리

OpenRouter는 사용한 만큼만 비용을 청구합니다.

**기본 모델 (google/gemini-3-flash-preview):**

- 입력: $0.075 / 1M tokens
- 출력: $0.30 / 1M tokens
- 예상 비용: 질문 평가 1회 약 $0.0005 (0.7원), 면접 완료 평가 1회 약 $0.001 (1.4원)

**기타 추천 모델:**

- `google/gemini-flash-1.5-8b` - 더 저렴 ($0.0375 / 1M tokens)
- `google/gemini-2.0-flash-exp:free` - 무료 (하루 10회 제한)

**비용 확인:**

- OpenRouter 대시보드: https://openrouter.ai/activity

## 문제 해결

### OpenRouter API 키 오류

```
AI 평가 실패: 401 Unauthorized
```

→ `.env` 파일의 `OPENROUTER_API_KEY`가 올바른지 확인하세요.

### Windows 인코딩 오류 (이모지/한글 깨짐)

```powershell
# PowerShell에서 실행 전 UTF-8 설정
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING="utf-8"
$env:APP_NAME="AI Interview Service"
```

또는 `RUN_AI_TESTS.ps1` 스크립트를 사용하세요 (자동 설정됨).

### 모델을 찾을 수 없음

```
AI 평가 실패: Model not found
```

→ 모델 이름이 올바른지 확인하세요. https://openrouter.ai/models

### 속도 제한

```
AI 평가 실패: 429 Too Many Requests
```

→ 무료 모델의 경우 사용 제한이 있습니다. 유료 모델로 변경하거나 시간을 두고 재시도하세요.

## 라이선스

MIT
