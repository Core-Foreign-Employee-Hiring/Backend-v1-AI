FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# UV 캐시 활용을 위해 의존성 파일 먼저 복사
COPY pyproject.toml README.md ./

# 의존성 설치
RUN uv sync --no-dev

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["uv", "run", "run.py"]

