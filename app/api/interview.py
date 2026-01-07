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
    InterviewSetQuestion,
    InterviewSetStatus,
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


def check_and_update_interview_status(db: "DB", set_id: UUID) -> bool:
    """
    면접 세트의 모든 답변이 완료되었는지 확인하고, 완료 시 상태를 pending_evaluation으로 변경합니다.
    
    조건:
    - 세트에 포함된 모든 질문에 대해 답변이 있어야 함
    - 꼬리질문이 있는 답변은 꼬리질문 답변도 있어야 함
    
    Returns:
        True if status was changed to pending_evaluation, False otherwise
    """
    # 면접 세트 조회
    interview_set = db.get(InterviewSet, set_id)
    if not interview_set or interview_set.status != InterviewSetStatus.IN_PROGRESS.value:
        return False
    
    # 세트에 포함된 질문 개수
    set_questions = db.exec(
        select(InterviewSetQuestion).where(InterviewSetQuestion.set_id == set_id)
    ).all()
    total_questions = len(set_questions)
    
    if total_questions == 0:
        return False
    
    # 답변 조회
    answers = db.exec(
        select(InterviewAnswer).where(InterviewAnswer.set_id == set_id)
    ).all()
    
    # 모든 질문에 답변했는지 확인
    if len(answers) < total_questions:
        return False
    
    # 꼬리질문이 있는 답변은 꼬리질문 답변도 있는지 확인
    for answer in answers:
        if answer.follow_up_question and not answer.follow_up_answer:
            return False
    
    # 모든 조건 충족: 상태를 pending_evaluation으로 변경
    interview_set.status = InterviewSetStatus.PENDING_EVALUATION.value
    db.add(interview_set)
    db.commit()
    return True


@router.post(
    "/sets",
    response_model=InterviewSetCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="면접 세트 생성",
    description="""
새로운 면접 세트를 생성하고 질문을 배정합니다.

**질문 조합 비율:**
- 공통 질문: 40%
- 직무 질문: 30%
- 외국인특화 질문: 30%

**상태 흐름:**
1. 생성 시: `in_progress` (면접중)
2. 모든 답변 완료 시: `pending_evaluation` (평가대기) - 자동 전환
3. 평가 완료 시: `completed` (평가완료)
""",
    responses={
        201: {"description": "면접 세트 생성 성공 - set_id와 배정된 질문 목록 반환"},
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
        now = datetime.now(timezone.utc)
        title = (body.title or "").strip() or f"{body.job_type.value.upper()} {body.level.value.upper()} 면접 ({now.date().isoformat()})"
        
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
            title=title,
            job_type=body.job_type.value,
            level=body.level.value,
            status=InterviewSetStatus.IN_PROGRESS.value,
        )
        db.add(interview_set)
        db.commit()
        db.refresh(interview_set)

        # 생성된 질문 목록을 DB에 저장 (이어하기 기능용)
        set_questions = []
        for idx, q in enumerate(selected_questions):
            set_questions.append(
                InterviewSetQuestion(
                    set_id=interview_set.id,
                    question_id=q.id,
                    question_order=idx + 1,
                    category=q.category,
                )
            )
        for sq in set_questions:
            db.add(sq)
        db.commit()

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
    description="""
면접 질문에 대한 답변을 제출합니다.

**꼬리질문 기능:**
- `enable_follow_up: true`로 설정하면 AI가 압박 꼬리질문을 생성합니다.
- 생성된 꼬리질문은 `/follow-up-answers` API로 답변해야 합니다.

**자동 상태 전환:**
- 꼬리질문이 없는 마지막 질문 답변 시, 모든 답변이 완료되었으면 `pending_evaluation`으로 자동 전환됩니다.

**중복 방지:**
- 같은 `set_id` + `question_order`로 중복 제출 시 409 에러가 발생합니다.
""",
    responses={
        200: {"description": "답변 제출 성공 - answer_id와 꼬리질문(있는 경우) 반환"},
        409: {
            "description": "중복 답변 - 동일한 면접 세트의 동일한 질문(order)에 이미 답변이 존재함",
            "content": {
                "application/json": {
                    "examples": {
                        "duplicate_answer": {
                            "summary": "중복 답변",
                            "value": {"detail": "이미 제출된 질문에 대한 답변이 존재합니다"},
                        }
                    }
                }
            },
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

        # 동일한 면접 세트의 동일한 질문(order)에 대해 중복 답변 제출 방지
        existing_answer = db.exec(
            select(InterviewAnswer)
            .where(InterviewAnswer.set_id == body.set_id)
            .where(InterviewAnswer.question_order == body.question_order)
        ).first()
        if existing_answer:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 제출된 질문에 대한 답변이 존재합니다",
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

        # 꼬리질문이 없으면 바로 상태 체크 (모든 답변 완료 시 pending_evaluation으로 전환)
        if not follow_up_question:
            check_and_update_interview_status(db, body.set_id)

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
    description="""
AI가 생성한 꼬리질문에 대한 답변을 제출합니다.

**사용 조건:**
- `/answers` API에서 `enable_follow_up: true`로 답변을 제출해야 꼬리질문이 생성됩니다.
- 반환된 `answer_id`를 사용하여 이 API를 호출합니다.

**자동 상태 전환:**
- 모든 질문과 꼬리질문 답변이 완료되면 면접 세트 상태가 `pending_evaluation`으로 자동 전환됩니다.
- 이후 `/sets/{set_id}/complete` API로 AI 평가를 요청할 수 있습니다.
""",
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

        # 상태 체크 (모든 답변 + 꼬리질문 답변 완료 시 pending_evaluation으로 전환)
        check_and_update_interview_status(db, answer.set_id)

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
    summary="면접 완료 및 AI 평가 생성",
    description="""
면접을 완료하고 AI 종합 평가를 생성합니다.

**호출 조건:**
- 면접 세트 상태가 `pending_evaluation`이어야 합니다.
- 모든 질문에 답변하고, 꼬리질문이 있는 경우 꼬리질문 답변도 완료해야 합니다.
- 상태는 답변 제출 시 자동으로 `pending_evaluation`으로 전환됩니다.

**평가 항목 (각 0-100점):**
- logic: 논리성 - 답변의 논리적 구조와 일관성
- evidence: 근거 - 구체적인 사례와 근거 제시
- job_understanding: 직무이해도 - 지원 직무에 대한 이해도
- formality: 한국어 격식 - 비즈니스 한국어 사용 적절성
- completeness: 완성도 - 답변의 완성도와 충실성

**결과:**
- 평가 완료 후 상태가 `completed`로 변경됩니다.
- 종합 피드백과 질문별 상세 피드백이 반환됩니다.
""",
    responses={
        200: {"description": "면접 평가 완료 - 5가지 항목 점수와 피드백 반환"},
        400: {
            "description": "평가 불가 - 답변이 완료되지 않음",
            "content": {
                "application/json": {
                    "examples": {
                        "not_ready": {
                            "summary": "평가 대기 상태가 아님",
                            "value": {
                                "detail": "아직 모든 답변이 완료되지 않았습니다. 모든 질문에 답변하고, 꼬리질문이 있는 경우 꼬리질문 답변도 완료해주세요."
                            }
                        },
                        "already_completed": {
                            "summary": "이미 평가 완료됨",
                            "value": {"detail": "이미 평가가 완료된 면접 세트입니다"}
                        },
                        "no_answers": {
                            "summary": "답변 없음",
                            "value": {"detail": "답변이 없습니다"}
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

        # 상태 확인: 이미 평가 완료된 경우
        if interview_set.status == InterviewSetStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 평가가 완료된 면접 세트입니다"
            )

        # 상태 확인: 평가 대기 상태가 아닌 경우 (아직 답변이 완료되지 않음)
        if interview_set.status != InterviewSetStatus.PENDING_EVALUATION.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="아직 모든 답변이 완료되지 않았습니다. 모든 질문에 답변하고, 꼬리질문이 있는 경우 꼬리질문 답변도 완료해주세요."
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
            question_text = question.question if question else None

            answers_data.append(
                {
                    "question": question_text or "알 수 없는 질문",
                    "question_id": str(answer.question_id),
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
        interview_set.status = InterviewSetStatus.COMPLETED.value
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
    summary="면접 세트 상세 조회",
    description="""
면접 세트의 상세 정보를 조회합니다.

**이어하기 기능:**
- `questions`: 원래 배정된 질문 목록 (순서 포함)
- `answers`: 지금까지 제출된 답변 목록
- `next_question_order`: 다음에 답할 질문 순서 (모든 답변 완료 시 null)

**사용 예시:**
1. 중단된 면접 세트의 set_id로 이 API 호출
2. `next_question_order`로 다음 질문 확인
3. `questions`에서 해당 order의 질문 찾아서 사용자에게 표시
4. 답변 제출 후 다시 이 API 호출하여 진행 상황 확인
""",
    responses={
        200: {"description": "면접 세트 상세 정보 반환"},
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

    # 세트에 포함된 질문 목록 조회 (이어하기용)
    set_question_rows = db.exec(
        select(InterviewSetQuestion, Question)
        .join(Question, InterviewSetQuestion.question_id == Question.id)
        .where(InterviewSetQuestion.set_id == set_id)
        .order_by(InterviewSetQuestion.question_order)
    ).all()

    questions_info: list[QuestionInfo] = []
    for sq, q in set_question_rows:
        questions_info.append(
            QuestionInfo(
                id=q.id,
                question=q.question,
                order=sq.question_order,
                category=sq.category,
            )
        )

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

    # 다음 질문 order 계산 (질문 목록이 있으면, 아직 답하지 않은 가장 작은 order)
    answered_orders = {a.question_order for a in answers}
    next_order = None
    for qi in questions_info:
        if qi.order not in answered_orders:
            next_order = qi.order
            break

    return InterviewSetDetailResponse(
        set=InterviewSetResponse.model_validate(interview_set),
        questions=questions_info,
        answers=answers_with_questions,
        evaluation=evaluation_response,
        next_question_order=next_order,
    )


@router.get(
    "/sets",
    response_model=list[InterviewSetResponse],
    summary="면접 세트 목록 조회",
    description="""
현재 로그인한 사용자의 면접 세트 목록을 조회합니다.

**정렬:** 최신순 (created_at 내림차순)

**상태별 의미:**
- `in_progress`: 면접중 - 아직 답변이 완료되지 않음
- `pending_evaluation`: 평가대기 - 모든 답변 완료, AI 평가 대기
- `completed`: 평가완료 - AI 평가까지 완료됨
""",
    responses={
        200: {"description": "면접 세트 목록 반환 (최신순 정렬)"},
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

