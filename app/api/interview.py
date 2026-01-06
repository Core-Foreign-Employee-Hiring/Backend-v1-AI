import json
import random
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlmodel import desc, select

from app.core.auth import CurrentUser, DB
from app.models import (
    InterviewAnswer,
    InterviewEvaluation,
    InterviewSet,
    Question,
)
from app.schemas import (
    InterviewAnswerResponse,
    InterviewEvaluationResponse,
    InterviewSetCreate,
    InterviewSetCreateResponse,
    InterviewSetDetailResponse,
    InterviewSetResponse,
    QuestionInfo,
    QuestionResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    SubmitFollowUpRequest,
    SubmitFollowUpResponse,
)

router = APIRouter(prefix="/interview", tags=["Interview"])


def shuffle_array(arr: list) -> list:
    """배열을 랜덤하게 섞습니다."""
    shuffled = arr.copy()
    random.shuffle(shuffled)
    return shuffled


@router.post(
    "/sets",
    response_model=InterviewSetCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="면접 세트 생성",
    description="질문 개수를 선택하여 면접 세트를 생성합니다.",
    responses={
        201: {"description": "면접 세트 생성 성공"},
        400: {
            "description": "질문 부족 - 데이터베이스에 충분한 질문이 없음",
            "content": {
                "application/json": {
                    "examples": {
                        "insufficient_questions": {
                            "summary": "질문 부족",
                            "value": {
                                "detail": "데이터베이스에 충분한 질문이 없습니다. 요청: 5개, 사용 가능: 2개. (공통: 1, 직무(it): 1, 외국인특화: 0)"
                            }
                        }
                    }
                }
            }
        },
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
        500: {"description": "서버 오류"},
    },
)
def create_interview_set(body: InterviewSetCreate, db: DB, current_user: CurrentUser):
    """
    면접 세트를 생성합니다.
    
    질문 조합: 공통 40%, 직무 30%, 외국인 30% 비율로 선택
    """
    try:
        user_id = current_user["sub"]
        
        # 질문 조합 (면접 세트 생성 전에 먼저 확인)
        question_count = body.question_count
        common_count = int(question_count * 0.4)
        job_count = int(question_count * 0.3)
        foreigner_count = question_count - common_count - job_count

        # 공통 질문
        common_questions = db.exec(
            select(Question).where(Question.category == "common").limit(20)
        ).all()

        # 직무 질문
        job_questions = db.exec(
            select(Question)
            .where(Question.category == "job")
            .where(Question.job_type == body.job_type.value)
            .limit(20)
        ).all()

        # 외국인특화 질문
        foreigner_questions = db.exec(
            select(Question).where(Question.category == "foreigner").limit(20)
        ).all()

        # 랜덤 선택
        selected_questions = [
            *shuffle_array(common_questions)[:min(common_count, len(common_questions))],
            *shuffle_array(job_questions)[:min(job_count, len(job_questions))],
            *shuffle_array(foreigner_questions)[
                :min(foreigner_count, len(foreigner_questions))
            ],
        ][:question_count]

        # 질문이 충분하지 않으면 에러 (면접 세트 생성 전에 확인)
        if len(selected_questions) < question_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"데이터베이스에 충분한 질문이 없습니다. "
                       f"요청: {question_count}개, 사용 가능: {len(selected_questions)}개. "
                       f"(공통: {len(common_questions)}, 직무({body.job_type.value}): {len(job_questions)}, "
                       f"외국인특화: {len(foreigner_questions)})"
            )
        
        # 질문이 충분하면 면접 세트 생성
        interview_set = InterviewSet(
            user_id=user_id,
            job_type=body.job_type.value,
            level=body.level.value,
            status="in_progress",
        )
        db.add(interview_set)
        db.commit()
        db.refresh(interview_set)

        # 응답 생성
        questions_info = [
            QuestionInfo(
                id=q.id,
                question=q.question,
                order=idx + 1,
                category=q.category,
            )
            for idx, q in enumerate(selected_questions)
        ]

        return InterviewSetCreateResponse(
            set_id=interview_set.id,
            questions=questions_info,
        )
    except HTTPException:
        # HTTPException은 그대로 다시 발생
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create interview set",
        ) from e


@router.post(
    "/answers",
    response_model=SubmitAnswerResponse,
    summary="답변 제출 및 꼬리질문 생성",
    description="면접 답변을 제출하고 필요시 꼬리질문을 생성합니다.",
    responses={
        200: {"description": "답변 제출 성공"},
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
                        "missing_fields": {
                            "summary": "필수 필드 누락",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "set_id",
                                        "message": "Field required",
                                        "type": "missing"
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
                                        "field": "set_id",
                                        "message": "Input should be a valid UUID",
                                        "type": "uuid_parsing"
                                    }
                                ]
                            }
                        },
                        "invalid_order": {
                            "summary": "잘못된 질문 순서",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "question_order",
                                        "message": "Input should be greater than 0",
                                        "type": "greater_than"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        },
        500: {"description": "서버 오류"},
    },
)
def submit_answer(body: SubmitAnswerRequest, db: DB, current_user: CurrentUser):
    """
    면접 답변을 제출합니다.
    
    - userAnswer 또는 audio 중 하나는 필수입니다.
    - enableFollowUp이 true면 AI가 꼬리질문을 생성합니다.
    """
    from app.lib.openrouter import generate_follow_up_question

    try:
        user_answer = body.user_answer or ""
        transcript = None

        # 음성 입력이면 전사
        if not user_answer and body.audio:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="음성 전사 기능은 아직 구현되지 않았습니다",
            )

        follow_up_question = None

        # 꼬리질문 생성
        if body.enable_follow_up:
            # 질문 조회 (선택적)
            question = db.get(Question, body.question_id)
            question_text = question.question if question else None

            try:
                follow_up_question = generate_follow_up_question(
                    question=question_text,
                    user_answer=user_answer,
                    ai_model=body.ai_model,
                )
            except Exception as e:
                # 꼬리질문 생성 실패해도 답변은 저장
                print(f"꼬리질문 생성 실패: {str(e)}")
                follow_up_question = None

        # 답변 저장
        answer = InterviewAnswer(
            set_id=body.set_id,
            question_id=body.question_id,
            question_order=body.question_order,
            user_answer=user_answer,
            follow_up_question=follow_up_question,
        )
        db.add(answer)
        db.commit()
        db.refresh(answer)

        return SubmitAnswerResponse(
            answer_id=answer.id,
            follow_up_question=follow_up_question,
            transcript=transcript,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit answer",
        ) from e


@router.post(
    "/follow-up-answers",
    response_model=SubmitFollowUpResponse,
    summary="꼬리질문 답변 제출",
    description="꼬리질문에 대한 답변을 제출합니다.",
    responses={
        200: {"description": "꼬리질문 답변 제출 성공"},
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
        404: {"description": "답변을 찾을 수 없음"},
        422: {
            "description": "유효성 검사 실패",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_answer_id": {
                            "summary": "답변 ID 누락",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "answer_id",
                                        "message": "Field required",
                                        "type": "missing"
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
                                        "field": "answer_id",
                                        "message": "Input should be a valid UUID",
                                        "type": "uuid_parsing"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        },
        500: {"description": "서버 오류"},
    },
)
def submit_follow_up_answer(body: SubmitFollowUpRequest, db: DB, current_user: CurrentUser):
    """꼬리질문에 대한 답변을 제출합니다."""
    try:
        answer = db.get(InterviewAnswer, body.answer_id)
        if not answer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found"
            )

        follow_up_answer = body.follow_up_answer or ""
        transcript = None

        # 음성 입력이면 전사 (TODO: 실제 구현)
        if not follow_up_answer and body.audio:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="음성 전사 기능은 아직 구현되지 않았습니다",
            )

        answer.follow_up_answer = follow_up_answer
        db.add(answer)
        db.commit()

        return SubmitFollowUpResponse(success=True, transcript=transcript)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit follow-up answer",
        ) from e


@router.post(
    "/sets/{set_id}/complete",
    response_model=InterviewEvaluationResponse,
    summary="면접 완료 및 평가 생성",
    description="면접을 완료하고 AI 평가를 생성합니다.",
    responses={
        200: {"description": "면접 평가 완료"},
        400: {"description": "답변이 없습니다"},
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
        403: {"description": "권한 없음 (다른 사용자의 면접 세트)"},
        404: {"description": "면접 세트를 찾을 수 없음"},
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
                                        "field": "set_id",
                                        "message": "Input should be a valid UUID",
                                        "type": "uuid_parsing"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        },
        500: {"description": "서버 오류 - AI 평가 실패"},
    },
)
def complete_interview(set_id: UUID, db: DB, current_user: CurrentUser):
    """면접을 완료하고 AI 평가를 생성합니다."""
    from app.lib.openrouter import evaluate_interview_comprehensive

    try:
        user_id = current_user["sub"]
        
        # 면접 세트 조회
        interview_set = db.get(InterviewSet, set_id)
        if not interview_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Interview set not found"
            )
        
        # 본인의 면접 세트인지 확인
        if interview_set.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="다른 사용자의 면접 세트는 완료할 수 없습니다"
            )

        # 답변 조회
        answers = db.exec(
            select(InterviewAnswer)
            .where(InterviewAnswer.set_id == set_id)
            .order_by(InterviewAnswer.question_order)
        ).all()

        if not answers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="답변이 없습니다"
            )

        # 질문 정보와 함께 답변 데이터 준비
        answers_data = []
        for answer in answers:
            question = db.get(Question, answer.question_id)
            answers_data.append(
                {
                    "question": question.question if question else "알 수 없는 질문",
                    "user_answer": answer.user_answer,
                    "follow_up_question": answer.follow_up_question,
                    "follow_up_answer": answer.follow_up_answer,
                }
            )

        # AI 종합 평가
        try:
            evaluation_data = evaluate_interview_comprehensive(answers_data)
        except Exception as e:
            # 에러 로그 출력
            import traceback
            print(f"AI 평가 실패: {str(e)}")
            print(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI 평가 실패: {str(e)}",
            )

        # 평가 저장
        evaluation = InterviewEvaluation(
            set_id=set_id,
            logic=evaluation_data["logic"],
            evidence=evaluation_data["evidence"],
            job_understanding=evaluation_data["jobUnderstanding"],
            formality=evaluation_data["formality"],
            completeness=evaluation_data["completeness"],
            overall_feedback=evaluation_data["overallFeedback"],
            detailed_feedback=json.dumps(
                evaluation_data["detailedFeedback"], ensure_ascii=False
            ),
        )
        db.add(evaluation)

        # 면접 세트 완료 처리
        interview_set.status = "completed"
        interview_set.completed_at = datetime.now(timezone.utc)
        db.add(interview_set)

        db.commit()
        db.refresh(evaluation)

        return InterviewEvaluationResponse(
            id=evaluation.id,
            set_id=evaluation.set_id,
            logic=evaluation.logic,
            evidence=evaluation.evidence,
            job_understanding=evaluation.job_understanding,
            formality=evaluation.formality,
            completeness=evaluation.completeness,
            overall_feedback=evaluation.overall_feedback,
            detailed_feedback=json.loads(evaluation.detailed_feedback),
            created_at=evaluation.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete interview",
        ) from e


@router.get(
    "/sets/{set_id}",
    response_model=InterviewSetDetailResponse,
    summary="면접 세트 조회",
    description="면접 세트의 상세 정보를 조회합니다.",
    responses={
        200: {"description": "면접 세트 조회 성공"},
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
        403: {"description": "권한 없음 (다른 사용자의 면접 세트)"},
        404: {"description": "면접 세트를 찾을 수 없음"},
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
                                        "field": "set_id",
                                        "message": "Input should be a valid UUID",
                                        "type": "uuid_parsing"
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
def get_interview_set(set_id: UUID, db: DB, current_user: CurrentUser):
    """면접 세트의 상세 정보를 조회합니다."""
    user_id = current_user["sub"]
    
    interview_set = db.get(InterviewSet, set_id)
    if not interview_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Interview set not found"
        )
    
    # 본인의 면접 세트인지 확인
    if interview_set.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 사용자의 면접 세트는 조회할 수 없습니다"
        )

    # 답변 조회
    answers = db.exec(
        select(InterviewAnswer)
        .where(InterviewAnswer.set_id == set_id)
        .order_by(InterviewAnswer.question_order)
    ).all()

    # 각 답변에 질문 정보 추가
    answers_with_questions = []
    for answer in answers:
        question = db.get(Question, answer.question_id)
        answer_response = InterviewAnswerResponse(
            id=answer.id,
            set_id=answer.set_id,
            question_id=answer.question_id,
            question_order=answer.question_order,
            user_answer=answer.user_answer,
            follow_up_question=answer.follow_up_question,
            follow_up_answer=answer.follow_up_answer,
            created_at=answer.created_at,
            question=QuestionResponse.model_validate(question) if question else None,
        )
        answers_with_questions.append(answer_response)

    # 평가 조회
    evaluation = db.exec(
        select(InterviewEvaluation).where(InterviewEvaluation.set_id == set_id)
    ).first()

    evaluation_response = None
    if evaluation:
        evaluation_response = InterviewEvaluationResponse(
            id=evaluation.id,
            set_id=evaluation.set_id,
            logic=evaluation.logic,
            evidence=evaluation.evidence,
            job_understanding=evaluation.job_understanding,
            formality=evaluation.formality,
            completeness=evaluation.completeness,
            overall_feedback=evaluation.overall_feedback,
            detailed_feedback=json.loads(evaluation.detailed_feedback),
            created_at=evaluation.created_at,
        )

    return InterviewSetDetailResponse(
        set=InterviewSetResponse.model_validate(interview_set),
        answers=answers_with_questions,
        evaluation=evaluation_response,
    )


@router.get(
    "/sets",
    response_model=list[InterviewSetResponse],
    summary="면접 세트 목록",
    description="현재 로그인한 사용자의 면접 세트 목록을 조회합니다.",
    responses={
        200: {"description": "면접 세트 목록 조회 성공"},
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
def list_interview_sets(db: DB, current_user: CurrentUser):
    """현재 로그인한 사용자의 면접 세트 목록을 조회합니다."""
    user_id = current_user["sub"]
    sets = db.exec(
        select(InterviewSet)
        .where(InterviewSet.user_id == user_id)
        .order_by(desc(InterviewSet.created_at))
    ).all()
    return sets

