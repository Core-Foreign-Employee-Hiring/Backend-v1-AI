from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlmodel import desc, select

from app.core.auth import CurrentUser, DB
from app.models import Question
from app.schemas import (
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
)

router = APIRouter(prefix="/admin/questions", tags=["Admin - Questions"])


@router.get(
    "",
    response_model=list[QuestionResponse],
    summary="질문 목록 조회 (어드민 전용)",
    description="모든 질문 목록을 조회합니다. (나중에 어드민 권한 필요)",
    responses={
        200: {"description": "질문 목록 조회 성공"},
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
def list_questions(db: DB, current_user: CurrentUser):
    """질문 목록을 조회합니다."""
    questions = db.exec(select(Question).order_by(desc(Question.created_at))).all()
    return questions


@router.get(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="질문 상세 조회 (어드민 전용)",
    description="특정 질문의 상세 정보를 조회합니다. (나중에 어드민 권한 필요)",
    responses={
        200: {"description": "질문 상세 조회 성공"},
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
        404: {
            "description": "질문을 찾을 수 없음",
            "content": {
                "application/json": {"example": {"detail": "Question not found"}}
            },
        }
    },
)
def get_question(question_id: UUID, db: DB, current_user: CurrentUser):
    """질문 상세 정보를 조회합니다."""
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )
    return question


@router.post(
    "",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="질문 등록 (어드민 전용)",
    description="새로운 질문을 등록합니다. (나중에 어드민 권한 필요)",
    responses={
        201: {"description": "질문 생성 성공"},
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
        422: {
            "description": "유효성 검사 실패",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_required": {
                            "summary": "필수 필드 누락",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "question",
                                        "message": "Field required",
                                        "type": "missing"
                                    }
                                ]
                            }
                        },
                        "invalid_category": {
                            "summary": "잘못된 카테고리",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "category",
                                        "message": "Input should be 'common', 'job' or 'foreigner'",
                                        "type": "enum"
                                    }
                                ]
                            }
                        },
                        "invalid_job_type": {
                            "summary": "잘못된 직무 타입",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "job_type",
                                        "message": "Input should be 'it' or 'marketing'",
                                        "type": "enum"
                                    }
                                ]
                            }
                        },
                        "invalid_level": {
                            "summary": "잘못된 레벨",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "level",
                                        "message": "Input should be 'intern', 'entry' or 'experienced'",
                                        "type": "enum"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        },
    },
)
def create_question(body: QuestionCreate, db: DB, current_user: CurrentUser):
    """새로운 질문을 등록합니다."""
    question = Question(
        question=body.question,
        category=body.category,
        job_type=body.job_type.value if body.job_type else None,
        level=body.level.value if body.level else None,
        model_answer=body.model_answer,
        reasoning=body.reasoning,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.put(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="질문 수정 (어드민 전용)",
    description="기존 질문을 수정합니다. (나중에 어드민 권한 필요)",
    responses={
        200: {"description": "질문 수정 성공"},
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
                        "invalid_category": {
                            "summary": "잘못된 카테고리",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "category",
                                        "message": "Input should be 'common', 'job' or 'foreigner'",
                                        "type": "enum"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        },
    },
)
def update_question(question_id: UUID, body: QuestionUpdate, db: DB, current_user: CurrentUser):
    """질문을 수정합니다."""
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )

    question.question = body.question
    question.category = body.category
    question.job_type = body.job_type.value if body.job_type else None
    question.level = body.level.value if body.level else None
    question.model_answer = body.model_answer
    question.reasoning = body.reasoning

    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="질문 삭제 (어드민 전용)",
    description="질문을 삭제합니다. (나중에 어드민 권한 필요)",
    responses={
        204: {"description": "질문 삭제 성공"},
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
    },
)
def delete_question(question_id: UUID, db: DB, current_user: CurrentUser):
    """질문을 삭제합니다."""
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )

    db.delete(question)
    db.commit()

