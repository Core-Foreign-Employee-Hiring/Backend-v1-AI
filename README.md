# 면접 AI 서비스 API

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

## 테스트

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

```bash
# 전체 AI 테스트
uv run pytest tests/test_ai_integration.py -v -s

# 개별 테스트
uv run pytest tests/test_ai_integration.py::test_ai_answer_evaluation_detailed -v -s
uv run pytest tests/test_ai_integration.py::test_ai_follow_up_question_generation -v -s
uv run pytest tests/test_ai_integration.py::test_ai_comprehensive_interview_evaluation -v -s
```
