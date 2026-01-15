from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func
from sqlmodel import desc, select

from app.core.auth import DB, CurrentUser
from app.models import AnswerNote, AnswerNoteEntry, Question
from app.schemas import (
    AnswerNoteCreate,
    AnswerNoteDetailResponse,
    AnswerNoteEntryCreate,
    AnswerNoteEntryResponse,
    AnswerNoteEntryUpdate,
    AnswerNoteSummaryResponse,
    AnswerNoteUpdate,
)

router = APIRouter(prefix="/answer-notes", tags=["Answer Notes"])


@router.get(
    "",
    response_model=list[AnswerNoteSummaryResponse],
    summary="답변 노트 목록 조회",
    description="""
현재 로그인한 사용자의 답변 노트 목록을 조회합니다.

**답변 노트란?**
- 면접 질문에 대해 사용자가 작성한 답변과 피드백을 저장하는 공간
- 면접 세트와는 별개로, 개별 질문에 대한 학습/연습용

**정렬:** 최근 수정순 (updated_at 내림차순)

**응답 필드:**
- `title`: 노트 제목
- `entries_count`: 노트에 포함된 답변 항목 수
""",
    responses={
        200: {"description": "답변 노트 목록 반환 (최근 수정순)"},
        401: {
            "description": "인증 실패 또는 유효하지 않은 토큰",
            "content": {
                "application/json": {
                    "examples": {
                        "not_authenticated": {"summary": "인증되지 않음", "value": {"detail": "Not authenticated"}},
                        "invalid_token": {
                            "summary": "유효하지 않은 토큰",
                            "value": {"detail": "유효하지 않거나 만료된 토큰입니다"},
                        },
                    }
                }
            },
        },
    },
)
def list_answer_notes(db: DB, current_user: CurrentUser):
    """현재 로그인한 사용자의 답변 노트 목록을 조회합니다."""
    user_id = current_user["sub"]
    counts_subq = (
        select(
            AnswerNoteEntry.note_id,
            func.count(AnswerNoteEntry.id).label("entries_count"),
        )
        .group_by(AnswerNoteEntry.note_id)
        .subquery()
    )

    rows = db.exec(
        select(
            AnswerNote,
            func.coalesce(counts_subq.c.entries_count, 0),
        )
        .outerjoin(counts_subq, AnswerNote.id == counts_subq.c.note_id)
        .where(AnswerNote.user_id == user_id)
        .order_by(desc(AnswerNote.updated_at))
    ).all()

    return [
        AnswerNoteSummaryResponse(
            id=note.id,
            title=note.title,
            entries_count=entries_count,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )
        for note, entries_count in rows
    ]


@router.get(
    "/{note_id}",
    response_model=AnswerNoteDetailResponse,
    summary="답변 노트 상세 조회",
    description="""
답변 노트의 상세 정보를 조회합니다.

**응답 구성:**
- 노트 기본 정보 (title, created_at, updated_at)
- 노트에 포함된 답변 항목 목록
""",
    responses={
        200: {"description": "답변 노트 상세 정보 반환"},
        401: {
            "description": "인증 실패 또는 유효하지 않은 토큰",
            "content": {
                "application/json": {
                    "examples": {
                        "not_authenticated": {
                            "summary": "인증되지 않음",
                            "value": {"detail": "Not authenticated"},
                        },
                        "invalid_token": {
                            "summary": "유효하지 않은 토큰",
                            "value": {"detail": "유효하지 않거나 만료된 토큰입니다"},
                        },
                    }
                }
            },
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
                                        "type": "uuid_parsing",
                                    }
                                ],
                            },
                        }
                    }
                }
            },
        },
    },
)
def get_answer_note(note_id: UUID, db: DB, current_user: CurrentUser):
    """답변 노트 상세 정보를 조회합니다."""
    user_id = current_user["sub"]
    note = db.get(AnswerNote, note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer note not found")

    if note.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 사용자의 답변 노트는 조회할 수 없습니다",
        )

    entries = db.exec(
        select(AnswerNoteEntry).where(AnswerNoteEntry.note_id == note.id).order_by(desc(AnswerNoteEntry.updated_at))
    ).all()

    return AnswerNoteDetailResponse(
        id=note.id,
        title=note.title,
        created_at=note.created_at,
        updated_at=note.updated_at,
        entries=[AnswerNoteEntryResponse.model_validate(item) for item in entries],
    )


@router.post(
    "",
    response_model=AnswerNoteDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="답변 노트 생성",
    description="""
새로운 답변 노트를 생성합니다.

**사용 목적:**
- 특정 질문에 대한 답변을 연습하고 기록
- 피드백을 받으며 답변을 개선하는 과정 저장

**필수 필드:**
- `title`: 노트 제목

**선택 필드:**
- `entries`: 초기 답변 항목 리스트 (없으면 빈 노트로 생성)

**Tip:** 노트만 먼저 만든 뒤 `/answer-notes/{note_id}/entries`로 항목을 추가할 수 있습니다.
""",
    responses={
        201: {"description": "답변 노트 생성 성공 - 생성된 노트 상세 정보 반환"},
        401: {
            "description": "인증 실패 또는 유효하지 않은 토큰",
            "content": {
                "application/json": {
                    "examples": {
                        "not_authenticated": {"summary": "인증되지 않음", "value": {"detail": "Not authenticated"}},
                        "invalid_token": {
                            "summary": "유효하지 않은 토큰",
                            "value": {"detail": "유효하지 않거나 만료된 토큰입니다"},
                        },
                    }
                }
            },
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
                                "errors": [{"field": "title", "message": "Field required", "type": "missing"}],
                            },
                        },
                        "invalid_uuid": {
                            "summary": "잘못된 UUID 형식",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "entries.0.question_id",
                                        "message": "Input should be a valid UUID",
                                        "type": "uuid_parsing",
                                    }
                                ],
                            },
                        },
                        "empty_string": {
                            "summary": "빈 문자열",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "title",
                                        "message": "String should have at least 1 character",
                                        "type": "string_too_short",
                                    }
                                ],
                            },
                        },
                    }
                }
            },
        },
        404: {
            "description": "질문을 찾을 수 없음",
            "content": {"application/json": {"example": {"detail": "Question not found"}}},
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
            title=body.title,
        )
        db.add(note)
        db.commit()
        db.refresh(note)

        entries: list[AnswerNoteEntry] = []
        if body.entries:
            for entry in body.entries:
                question = db.get(Question, entry.question_id)
                if not question:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Question not found",
                    )
                entries.append(
                    AnswerNoteEntry(
                        note_id=note.id,
                        question_id=entry.question_id,
                        initial_answer=entry.initial_answer,
                        feedback=entry.feedback,
                        improvements=entry.improvements,
                        final_answer=entry.final_answer,
                    )
                )
            for item in entries:
                db.add(item)
            db.commit()

        return AnswerNoteDetailResponse(
            id=note.id,
            title=note.title,
            created_at=note.created_at,
            updated_at=note.updated_at,
            entries=[AnswerNoteEntryResponse.model_validate(item) for item in entries],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create answer note",
        ) from e


@router.put(
    "/{note_id}",
    response_model=AnswerNoteDetailResponse,
    summary="답변 노트 수정",
    description="""
답변 노트의 제목을 수정합니다.

**수정 가능 필드:**
- `title`: 노트 제목

**권한:** 본인이 생성한 노트만 수정 가능 (403 에러 발생)
""",
    responses={
        200: {"description": "답변 노트 수정 성공 - 수정된 노트 상세 정보 반환"},
        401: {
            "description": "인증 실패 또는 유효하지 않은 토큰",
            "content": {
                "application/json": {
                    "examples": {
                        "not_authenticated": {"summary": "인증되지 않음", "value": {"detail": "Not authenticated"}},
                        "invalid_token": {
                            "summary": "유효하지 않은 토큰",
                            "value": {"detail": "유효하지 않거나 만료된 토큰입니다"},
                        },
                    }
                }
            },
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
                                        "type": "uuid_parsing",
                                    }
                                ],
                            },
                        },
                        "empty_string": {
                            "summary": "빈 문자열",
                            "value": {
                                "detail": "유효성 검사 실패",
                                "errors": [
                                    {
                                        "field": "title",
                                        "message": "String should have at least 1 character",
                                        "type": "string_too_short",
                                    }
                                ],
                            },
                        },
                    }
                }
            },
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer note not found")

        # 본인의 노트인지 확인
        if note.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="다른 사용자의 답변 노트는 수정할 수 없습니다",
            )

        if body.title is not None:
            note.title = body.title

        note.updated_at = datetime.now(UTC)
        db.add(note)
        db.commit()
        db.refresh(note)

        entries = db.exec(
            select(AnswerNoteEntry).where(AnswerNoteEntry.note_id == note.id).order_by(desc(AnswerNoteEntry.updated_at))
        ).all()

        return AnswerNoteDetailResponse(
            id=note.id,
            title=note.title,
            created_at=note.created_at,
            updated_at=note.updated_at,
            entries=[AnswerNoteEntryResponse.model_validate(item) for item in entries],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update answer note",
        ) from e


@router.post(
    "/{note_id}/entries",
    response_model=AnswerNoteEntryResponse,
    summary="답변 노트 항목 추가",
    description="""
답변 노트에 새로운 질문 답변 항목을 추가합니다.

**필수 필드:**
- `question_id`: 연결할 질문 ID
- `initial_answer`: 처음 작성한 답변
""",
    responses={
        200: {"description": "답변 노트 항목 추가 성공"},
        401: {
            "description": "인증 실패 또는 유효하지 않은 토큰",
            "content": {
                "application/json": {
                    "examples": {
                        "not_authenticated": {
                            "summary": "인증되지 않음",
                            "value": {"detail": "Not authenticated"},
                        },
                        "invalid_token": {
                            "summary": "유효하지 않은 토큰",
                            "value": {"detail": "유효하지 않거나 만료된 토큰입니다"},
                        },
                    }
                }
            },
        },
        403: {"description": "권한 없음 (다른 사용자의 노트)"},
        404: {
            "description": "노트 또는 질문을 찾을 수 없음",
            "content": {
                "application/json": {
                    "examples": {
                        "note_not_found": {"summary": "노트 없음", "value": {"detail": "Answer note not found"}},
                        "question_not_found": {"summary": "질문 없음", "value": {"detail": "Question not found"}},
                    }
                }
            },
        },
        422: {"description": "유효성 검사 실패"},
        500: {"description": "서버 오류"},
    },
)
def create_answer_note_entry(note_id: UUID, body: AnswerNoteEntryCreate, db: DB, current_user: CurrentUser):
    """답변 노트 항목을 추가합니다."""
    try:
        user_id = current_user["sub"]
        note = db.get(AnswerNote, note_id)
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer note not found")

        if note.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="다른 사용자의 답변 노트에는 항목을 추가할 수 없습니다",
            )

        question = db.get(Question, body.question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

        entry = AnswerNoteEntry(
            note_id=note.id,
            question_id=body.question_id,
            initial_answer=body.initial_answer,
            feedback=body.feedback,
            improvements=body.improvements,
            final_answer=body.final_answer,
        )
        db.add(entry)

        note.updated_at = datetime.now(UTC)
        db.add(note)

        db.commit()
        db.refresh(entry)

        return AnswerNoteEntryResponse.model_validate(entry)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create answer note entry",
        ) from e


@router.put(
    "/{note_id}/entries/{entry_id}",
    response_model=AnswerNoteEntryResponse,
    summary="답변 노트 항목 수정",
    description="""
답변 노트의 특정 항목을 수정합니다.

**전송한 필드만 업데이트됩니다 (PATCH 방식).**
""",
    responses={
        200: {"description": "답변 노트 항목 수정 성공"},
        401: {
            "description": "인증 실패 또는 유효하지 않은 토큰",
            "content": {
                "application/json": {
                    "examples": {
                        "not_authenticated": {
                            "summary": "인증되지 않음",
                            "value": {"detail": "Not authenticated"},
                        },
                        "invalid_token": {
                            "summary": "유효하지 않은 토큰",
                            "value": {"detail": "유효하지 않거나 만료된 토큰입니다"},
                        },
                    }
                }
            },
        },
        403: {"description": "권한 없음 (다른 사용자의 노트)"},
        404: {"description": "노트 또는 항목을 찾을 수 없음"},
        422: {"description": "유효성 검사 실패"},
        500: {"description": "서버 오류"},
    },
)
def update_answer_note_entry(
    note_id: UUID,
    entry_id: UUID,
    body: AnswerNoteEntryUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """답변 노트 항목을 수정합니다."""
    try:
        user_id = current_user["sub"]
        note = db.get(AnswerNote, note_id)
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer note not found")
        if note.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="다른 사용자의 답변 노트는 수정할 수 없습니다",
            )

        entry = db.get(AnswerNoteEntry, entry_id)
        if not entry or entry.note_id != note_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Answer note entry not found",
            )

        if body.initial_answer is not None:
            entry.initial_answer = body.initial_answer
        if body.feedback is not None:
            entry.feedback = body.feedback
        if body.improvements is not None:
            entry.improvements = body.improvements
        if body.final_answer is not None:
            entry.final_answer = body.final_answer

        entry.updated_at = datetime.now(UTC)
        note.updated_at = entry.updated_at

        db.add(entry)
        db.add(note)
        db.commit()
        db.refresh(entry)

        return AnswerNoteEntryResponse.model_validate(entry)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update answer note entry",
        ) from e


@router.delete(
    "/{note_id}/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="답변 노트 항목 삭제",
    description="답변 노트의 특정 항목을 삭제합니다.",
    responses={
        204: {"description": "답변 노트 항목 삭제 성공 (응답 본문 없음)"},
        401: {
            "description": "인증 실패 또는 유효하지 않은 토큰",
            "content": {
                "application/json": {
                    "examples": {
                        "not_authenticated": {
                            "summary": "인증되지 않음",
                            "value": {"detail": "Not authenticated"},
                        },
                        "invalid_token": {
                            "summary": "유효하지 않은 토큰",
                            "value": {"detail": "유효하지 않거나 만료된 토큰입니다"},
                        },
                    }
                }
            },
        },
        403: {"description": "권한 없음 (다른 사용자의 노트)"},
        404: {"description": "노트 또는 항목을 찾을 수 없음"},
        500: {"description": "서버 오류"},
    },
)
def delete_answer_note_entry(note_id: UUID, entry_id: UUID, db: DB, current_user: CurrentUser):
    """답변 노트 항목을 삭제합니다."""
    try:
        user_id = current_user["sub"]
        note = db.get(AnswerNote, note_id)
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer note not found")
        if note.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="다른 사용자의 답변 노트는 삭제할 수 없습니다",
            )

        entry = db.get(AnswerNoteEntry, entry_id)
        if not entry or entry.note_id != note_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Answer note entry not found",
            )

        db.delete(entry)
        note.updated_at = datetime.now(UTC)
        db.add(note)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete answer note entry",
        ) from e


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="답변 노트 삭제",
    description="""
답변 노트를 삭제합니다.

**주의사항:**
- 삭제된 노트는 복구할 수 없습니다.
- 노트에 포함된 답변 항목도 함께 삭제됩니다.
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
                        "not_authenticated": {"summary": "인증되지 않음", "value": {"detail": "Not authenticated"}},
                        "invalid_token": {
                            "summary": "유효하지 않은 토큰",
                            "value": {"detail": "유효하지 않거나 만료된 토큰입니다"},
                        },
                    }
                }
            },
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer note not found")

        # 본인의 노트인지 확인
        if note.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="다른 사용자의 답변 노트는 삭제할 수 없습니다"
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
