from fastapi import APIRouter, HTTPException, status

from app.lib.openrouter import analyze_specs_with_ai
from app.schemas import SpecsAnalyzeRequest, SpecsAnalyzeResponse

router = APIRouter(prefix="/specs", tags=["Specs"])


@router.post(
    "/analyze",
    response_model=SpecsAnalyzeResponse,
    summary="지원자 스펙 평가",
    description="""
외부 서버에서 호출 가능한 스펙 평가 API입니다.

**인증:** 토큰 검증 없이 호출 가능합니다.

지원자 스펙 텍스트를 입력하면 다음 5개 항목을 0~100으로 점수화하고 종합 분석을 반환합니다.
- experience
- certificate
- language
- career
- education
""",
    responses={
        200: {"description": "스펙 평가 성공"},
        422: {"description": "유효성 검사 실패"},
        500: {
            "description": "스펙 평가 실패",
            "content": {"application/json": {"example": {"detail": "AI analysis failed"}}},
        },
    },
)
def analyze_specs(body: SpecsAnalyzeRequest):
    """지원자 스펙 텍스트를 AI로 평가합니다."""
    try:
        result = analyze_specs_with_ai(specs=body.specs)
        return SpecsAnalyzeResponse(
            experience=result["experience"],
            certificate=result["certificate"],
            language=result["language"],
            career=result["career"],
            education=result["education"],
            analysis=result["analysis"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI analysis failed",
        ) from e
