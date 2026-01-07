from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import answer_notes, interview, questions
from app.core.database import create_db_and_tables, seed_initial_questions

from scalar_fastapi import get_scalar_api_reference


@asynccontextmanager
async def lifespan(_: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # 시작 시 데이터베이스 테이블 생성
    create_db_and_tables()
    
    # 초기 테스트 질문 시딩 (설정으로 ON/OFF 가능)
    seed_initial_questions()
    
    yield


app = FastAPI(
    title="면접 AI 서비스 API",
    summary="외국인을 위한 한국 취업 면접 준비 AI 서비스",
    description="""
## 인증 방법

모든 API는 JWT Bearer Token 인증이 필요합니다.

요청 헤더에 `Authorization: Bearer {access_token}` 추가
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Admin - Questions",
            "description": "질문 관리 - 나중에 어드민만 사용가능하게 할 것임임",
        },
        {
            "name": "Interview",
            "description": "면접 세트 및 평가 API",
        },
        {
            "name": "Answer Notes",
            "description": "답변 노트 관리 API",
        },
        {
            "name": "Health",
            "description": "서버 상태 확인",
        },
    ],
)

# CORS 설정 - 모든 도메인 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 예외 처리 핸들러 - 유효성 검사 에러를 깔끔하게 표시
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """유효성 검사 에러를 깔끔한 형식으로 반환"""
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": " -> ".join(str(x) for x in error["loc"][1:]),
                "message": error["msg"],
                "type": error["type"],
            }
        )
    return JSONResponse(
        status_code=422,
        content={"detail": "유효성 검사 실패", "errors": errors},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    """HTTP 예외를 깔끔한 형식으로 반환"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# 라우터 등록
app.include_router(questions.router)  # 어드민 전용: /admin/questions
app.include_router(interview.router)  # 일반 사용자: /interview
app.include_router(answer_notes.router)  # 일반 사용자: /answer-notes


@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        # Your OpenAPI document
        openapi_url=app.openapi_url,
        # Avoid CORS issues (optional)
        scalar_proxy_url="https://proxy.scalar.com",
    )

@app.get(
    "/health",
    tags=["Health"],
    summary="서버 상태 확인",
    description="서버가 정상 동작 중인지 확인합니다.",
    responses={
        200: {
            "description": "서버 정상",
            "content": {"application/json": {"example": {"status": "ok"}}},
        }
    },
)
def health():
    """서버 헬스체크 엔드포인트"""
    return {"status": "ok"}
