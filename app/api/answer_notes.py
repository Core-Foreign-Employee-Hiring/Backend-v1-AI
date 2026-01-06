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
    description="현재 로그인한 사용자의 답변 노트를 조회합니다.",
    responses={
        200: {"description": "답변 노트 목록 조회 성공"},
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
    description="새로운 답변 노트를 생성합니다.",
    responses={
        201: {"description": "답변 노트 생성 성공"},
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
    description="기존 답변 노트를 수정합니다.",
    responses={
        200: {"description": "답변 노트 수정 성공"},
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
    description="답변 노트를 삭제합니다.",
    responses={
        204: {"description": "답변 노트 삭제 성공"},
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

