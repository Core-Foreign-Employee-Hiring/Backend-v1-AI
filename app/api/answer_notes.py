from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlmodel import desc, select

from app.core.auth import CurrentUser, DB
from app.models import AnswerNote
from app.schemas import AnswerNoteCreate, AnswerNoteResponse, AnswerNoteUpdate

router = APIRouter(prefix="/answer-notes", tags=["Answer Notes"])


@router.get(
    "",
    response_model=list[AnswerNoteResponse],
    summary="답변 노트 목록 조회",
    description="""
현재 로그인한 사용자의 답변 노트 목록을 조회합니다.

**답변 노트란?**
- 면접 질문에 대해 사용자가 작성한 답변과 피드백을 저장하는 공간
- 면접 세트와는 별개로, 개별 질문에 대한 학습/연습용

**정렬:** 최근 수정순 (updated_at 내림차순)

**응답 필드:**
- `initial_answer`: 처음 작성한 답변
- `first_feedback`: 첫 번째 피드백 (수정 후)
- `second_feedback`: 두 번째 피드백 (수정 후)
- `final_answer`: 최종 정리된 답변
""",
    responses={
        200: {"description": "답변 노트 목록 반환 (최근 수정순)"},
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
def list_answer_notes(db: DB, current_user: CurrentUser):
    """현재 로그인한 사용자의 답변 노트 목록을 조회합니다."""
    user_id = current_user["sub"]
    notes = db.exec(
        select(AnswerNote)
        .where(AnswerNote.user_id == user_id)
        .order_by(desc(AnswerNote.updated_at))
    ).all()
    return notes


@router.post(
    "",
    response_model=AnswerNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="답변 노트 생성",
    description="""
새로운 답변 노트를 생성합니다.

**사용 목적:**
- 특정 질문에 대한 답변을 연습하고 기록
- 피드백을 받으며 답변을 개선하는 과정 저장

**필수 필드:**
- `question_id`: 연결할 질문 ID
- `initial_answer`: 처음 작성한 답변

**선택 필드:**
- `first_feedback`: 첫 번째 피드백
- `second_feedback`: 두 번째 피드백
- `final_answer`: 최종 정리된 답변

**Tip:** 처음에는 initial_answer만 작성하고, 나중에 PUT으로 피드백/최종답변을 추가할 수 있습니다.
""",
    responses={
        201: {"description": "답변 노트 생성 성공 - 생성된 노트 정보 반환"},
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
                                        "field": "question_id",
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
                                        "field": "question_id",
                                        "message": "Input should be a valid UUID",
                                        "type": "uuid_parsing"
                                    }
                                ]
                            }
                        },
                        "empty_string": {
                            "summary": "빈 문자열",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "initial_answer",
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
        500: {"description": "서버 오류"},
    },
)
def create_answer_note(body: AnswerNoteCreate, db: DB, current_user: CurrentUser):
    """새로운 답변 노트를 생성합니다."""
    try:
        user_id = current_user["sub"]
        note = AnswerNote(
            user_id=user_id,
            question_id=body.question_id,
            initial_answer=body.initial_answer,
            first_feedback=body.first_feedback,
            second_feedback=body.second_feedback,
            final_answer=body.final_answer,
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return note
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create answer note",
        ) from e


@router.put(
    "/{note_id}",
    response_model=AnswerNoteResponse,
    summary="답변 노트 수정",
    description="""
기존 답변 노트를 수정합니다.

**수정 가능 필드 (선택적):**
- `first_feedback`: 첫 번째 피드백
- `second_feedback`: 두 번째 피드백
- `final_answer`: 최종 정리된 답변

**특징:**
- 전송한 필드만 업데이트됩니다 (PATCH 방식 동작)
- null이 아닌 값만 기존 값을 덮어씁니다
- `initial_answer`와 `question_id`는 수정 불가 (생성 시 고정)

**권한:** 본인이 생성한 노트만 수정 가능 (403 에러 발생)
""",
    responses={
        200: {"description": "답변 노트 수정 성공 - 수정된 노트 정보 반환"},
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
        403: {"description": "권한 없음 (다른 사용자의 노트)"},
        404: {"description": "답변 노트를 찾을 수 없음"},
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
                                        "field": "note_id",
                                        "message": "Input should be a valid UUID",
                                        "type": "uuid_parsing"
                                    }
                                ]
                            }
                        },
                        "empty_string": {
                            "summary": "빈 문자열",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "final_answer",
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
        500: {"description": "서버 오류"},
    },
)
def update_answer_note(note_id: UUID, body: AnswerNoteUpdate, db: DB, current_user: CurrentUser):
    """답변 노트를 수정합니다."""
    try:
        user_id = current_user["sub"]
        note = db.get(AnswerNote, note_id)
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Answer note not found"
            )
        
        # 본인의 노트인지 확인
        if note.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="다른 사용자의 답변 노트는 수정할 수 없습니다"
            )

        if body.first_feedback is not None:
            note.first_feedback = body.first_feedback
        if body.second_feedback is not None:
            note.second_feedback = body.second_feedback
        if body.final_answer is not None:
            note.final_answer = body.final_answer

        note.updated_at = datetime.now(timezone.utc)
        db.add(note)
        db.commit()
        db.refresh(note)
        return note
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update answer note",
        ) from e


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="답변 노트 삭제",
    description="""
답변 노트를 삭제합니다.

**주의사항:**
- 삭제된 노트는 복구할 수 없습니다.
- 연결된 질문 데이터에는 영향을 주지 않습니다.

**권한:** 본인이 생성한 노트만 삭제 가능 (403 에러 발생)
""",
    responses={
        204: {"description": "답변 노트 삭제 성공 (응답 본문 없음)"},
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
        403: {"description": "권한 없음 (다른 사용자의 노트)"},
        404: {"description": "답변 노트를 찾을 수 없음"},
        500: {"description": "서버 오류"},
    },
)
def delete_answer_note(note_id: UUID, db: DB, current_user: CurrentUser):
    """답변 노트를 삭제합니다."""
    try:
        user_id = current_user["sub"]
        note = db.get(AnswerNote, note_id)
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Answer note not found"
            )
        
        # 본인의 노트인지 확인
        if note.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="다른 사용자의 답변 노트는 삭제할 수 없습니다"
            )

        db.delete(note)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete answer note",
        ) from e

