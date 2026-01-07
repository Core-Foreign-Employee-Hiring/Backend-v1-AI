# AGENTS.md

이 문서는 이 레포에서 AI 코딩 에이전트가 작업할 때 따라야 하는 **최소 규칙**을 정의합니다.

## API 변경 규칙 (FastAPI)

- **새 에러(HTTP status) 추가 시**
  - `HTTPException(status_code=...)`을 추가했다면, 해당 라우트 데코레이터의 `responses={...}`에 **동일한 status code + 예시 응답**을 반드시 추가한다.
  - 예: 409/400/403/404/422/500 등
- **요청/응답 형태 변경 시**
  - `app/schemas.py`(Pydantic)와 라우트의 `response_model`을 함께 업데이트한다.
- **권한/유저 범위 데이터**
  - `set_id`처럼 user-owned 리소스는 가능한 경우 **소유권 체크(403)** 를 추가한다.
