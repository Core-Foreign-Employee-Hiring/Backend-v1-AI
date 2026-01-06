from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlmodel import desc, select

from app.core.auth import CurrentUser, DB
from app.models import QAHistory, Question
from app.schemas import (
    QAHistoryResponse,
    QuestionEvaluateRequest,
    QuestionEvaluateResponse,
)

router = APIRouter(prefix="/practice", tags=["Practice"])


@router.post(
    "/evaluate",
    response_model=QuestionEvaluateResponse,
    summary="AI 답변 평가 (일반 사용자용)",
    description="사용자의 답변을 AI로 평가합니다. (음성 또는 텍스트)",
    responses={
        200: {"description": "평가 성공"},
        401: {
            "description": "인증 실패 또는 유효하지 않은 토큰",
            "content": {
                "application/json": {
                    "examples": {
                        "not_authenticated": {
                            "summary": "인증되지 않음",
                            "value": {"detail": "Not authenticated"}
                        },
                        "invalid_token": {
                            "summary": "유효하지 않은 토큰",
                            "value": {"detail": "유효하지 않거나 만료된 토큰입니다"}
                        }
                    }
                }
            }
        },
        404: {"description": "질문을 찾을 수 없음"},
        422: {
            "description": "유효성 검사 실패",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_answer": {
                            "summary": "답변 누락",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "user_answer",
                                        "message": "userAnswer 또는 audio 중 하나는 필수입니다",
                                        "type": "value_error"
                                    }
                                ]
                            }
                        },
                        "invalid_uuid": {
                            "summary": "잘못된 UUID 형식",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "question_id",
                                        "message": "Input should be a valid UUID",
                                        "type": "uuid_parsing"
                                    }
                                ]
                            }
                        },
                        "invalid_ai_model": {
                            "summary": "잘못된 AI 모델",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "ai_model",
                                        "message": "String should have at least 1 character",
                                        "type": "string_too_short"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        },
        500: {"description": "AI 평가 실패"},
    },
)
def evaluate_answer(body: QuestionEvaluateRequest, db: DB, current_user: CurrentUser):
    """
    사용자의 답변을 AI로 평가합니다.
    
    - userAnswer 또는 audio 중 하나는 필수입니다.
    - audio가 제공되면 음성을 텍스트로 변환 후 평가합니다.
    """
    from app.lib.openrouter import evaluate_answer_with_ai

    # 질문 조회
    question = db.get(Question, body.question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )

    user_answer = body.user_answer or ""
    transcript = None

    # 음성 입력이면 전사
    if not user_answer and body.audio:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="음성 전사 기능은 아직 구현되지 않았습니다",
        )

    # AI 평가
    try:
        evaluation = evaluate_answer_with_ai(
            question=question.question,
            model_answer=question.model_answer,
            reasoning=question.reasoning,
            user_answer=user_answer,
            ai_model=body.ai_model,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 평가 실패: {str(e)}",
        )

    # QA 히스토리 저장
    user_id = current_user["sub"]
    history = QAHistory(
        user_id=user_id,
        question_id=body.question_id,
        user_answer=user_answer,
        ai_model=body.ai_model,
        ai_response=evaluation.get("raw_response", str(evaluation)),
        score=evaluation["score"],
        hints=evaluation["hints"],
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return QuestionEvaluateResponse(
        score=evaluation["score"],
        hints=evaluation["hints"],
        strengths=evaluation.get("strengths"),
        improvements=evaluation.get("improvements"),
        history_id=history.id,
        transcript=transcript,
    )


@router.get(
    "/history/{question_id}",
    response_model=list[QAHistoryResponse],
    summary="QA 히스토리 조회 (일반 사용자용)",
    description="특정 질문에 대한 현재 사용자의 QA 히스토리를 조회합니다.",
    responses={
        200: {"description": "QA 히스토리 조회 성공"},
        401: {
            "description": "인증 실패 또는 유효하지 않은 토큰",
            "content": {
                "application/json": {
                    "examples": {
                        "not_authenticated": {
                            "summary": "인증되지 않음",
                            "value": {"detail": "Not authenticated"}
                        },
                        "invalid_token": {
                            "summary": "유효하지 않은 토큰",
                            "value": {"detail": "유효하지 않거나 만료된 토큰입니다"}
                        }
                    }
                }
            }
        },
    },
)
def get_qa_history(question_id: UUID, db: DB, current_user: CurrentUser):
    """특정 질문에 대한 현재 사용자의 QA 히스토리를 조회합니다."""
    user_id = current_user["sub"]
    history = db.exec(
        select(QAHistory)
        .where(QAHistory.question_id == question_id)
        .where(QAHistory.user_id == user_id)
        .order_by(desc(QAHistory.created_at))
    ).all()
    return history

