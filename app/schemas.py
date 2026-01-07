from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import JobType, Level

# === 질문 ===


class QuestionCreate(BaseModel):
    """질문 생성 요청"""

    question: str = Field(min_length=1, description="질문 내용")
    category: str = Field(pattern="^(common|job|foreigner)$", description="카테고리")
    job_type: JobType | None = Field(default=None, description="직무 타입")
    level: Level | None = Field(default=None, description="레벨")
    model_answer: str = Field(min_length=1, description="모범답안")
    reasoning: str = Field(min_length=1, description="모범답안의 논리와 이유")


class QuestionUpdate(QuestionCreate):
    """질문 수정 요청"""

    pass


class QuestionResponse(BaseModel):
    """질문 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question: str
    category: str
    job_type: str | None
    level: str | None
    model_answer: str
    reasoning: str
    created_at: datetime
    updated_at: datetime


class AudioInput(BaseModel):
    """음성 입력"""

    data: str = Field(min_length=1, description="Base64 인코딩된 오디오 데이터")
    format: str = Field(min_length=1, description="오디오 포맷")


class QuestionEvaluateRequest(BaseModel):
    """질문 평가 요청"""

    question_id: UUID = Field(description="질문 ID")
    user_answer: str | None = Field(default=None, min_length=1, description="사용자 답변")
    audio: AudioInput | None = Field(default=None, description="음성 입력")
    ai_model: str = Field(description="AI 모델명")


class QuestionEvaluateResponse(BaseModel):
    """질문 평가 응답"""

    score: int = Field(ge=0, le=100, description="점수")
    hints: str = Field(description="힌트와 피드백")
    strengths: str | None = Field(default=None, description="잘한 점")
    improvements: str | None = Field(default=None, description="개선이 필요한 점")
    history_id: UUID = Field(description="히스토리 ID")
    transcript: str | None = Field(default=None, description="음성 전사 텍스트")


# === 면접 세트 ===


class InterviewSetCreate(BaseModel):
    """면접 세트 생성 요청"""

    job_type: JobType = Field(description="직무 타입")
    level: Level = Field(description="레벨")
    question_count: int = Field(default=3, ge=1, le=10, description="질문 개수")


class QuestionInfo(BaseModel):
    """질문 정보"""

    id: UUID
    question: str
    order: int
    category: str


class InterviewSetCreateResponse(BaseModel):
    """면접 세트 생성 응답"""

    set_id: UUID
    questions: list[QuestionInfo]


class InterviewSetResponse(BaseModel):
    """면접 세트 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    job_type: str
    level: str
    status: str
    created_at: datetime
    completed_at: datetime | None


class SubmitAnswerRequest(BaseModel):
    """답변 제출 요청"""

    set_id: UUID = Field(description="면접 세트 ID")
    question_id: UUID = Field(description="질문 ID")
    question_order: int = Field(ge=1, description="질문 순서")
    user_answer: str | None = Field(default=None, min_length=1, description="사용자 답변")
    audio: AudioInput | None = Field(default=None, description="음성 입력")
    enable_follow_up: bool = Field(default=False, description="꼬리질문 활성화")
    ai_model: str | None = Field(default=None, description="AI 모델명")


class SubmitAnswerResponse(BaseModel):
    """답변 제출 응답"""

    answer_id: UUID
    follow_up_question: str | None
    transcript: str | None


class SubmitFollowUpRequest(BaseModel):
    """꼬리질문 답변 제출 요청"""

    answer_id: UUID = Field(description="답변 ID")
    follow_up_answer: str | None = Field(
        default=None, min_length=1, description="꼬리질문 답변"
    )
    audio: AudioInput | None = Field(default=None, description="음성 입력")


class SubmitFollowUpResponse(BaseModel):
    """꼬리질문 답변 제출 응답"""

    success: bool
    transcript: str | None


class InterviewAnswerResponse(BaseModel):
    """면접 답변 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    set_id: UUID
    question_id: UUID
    question_order: int
    user_answer: str
    follow_up_question: str | None
    follow_up_answer: str | None
    created_at: datetime
    question: QuestionResponse | None = None


class DetailedFeedbackItem(BaseModel):
    """상세 피드백 항목"""

    model_config = ConfigDict(populate_by_name=True)

    question_order: int = Field(alias="questionOrder")
    question: str  # 질문 내용
    user_answer: str = Field(alias="userAnswer")  # 사용자 답변
    follow_up_question: str | None = Field(default=None, alias="followUpQuestion")  # 꼬리질문
    follow_up_answer: str | None = Field(default=None, alias="followUpAnswer")  # 꼬리질문 답변
    feedback: str  # AI 피드백
    improvements: str  # 개선 제안


class InterviewEvaluationResponse(BaseModel):
    """면접 평가 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    set_id: UUID
    logic: int
    evidence: int
    job_understanding: int
    formality: int
    completeness: int
    overall_feedback: str
    detailed_feedback: list[DetailedFeedbackItem]
    created_at: datetime


class InterviewSetDetailResponse(BaseModel):
    """면접 세트 상세 응답"""

    set: InterviewSetResponse
    questions: list[QuestionInfo] = Field(default_factory=list, description="면접 세트에 포함된 질문 목록 (이어하기용)")
    answers: list[InterviewAnswerResponse]
    evaluation: InterviewEvaluationResponse | None
    next_question_order: int | None = Field(default=None, description="다음에 답할 질문 순서(없으면 None)")


# === 답변 노트 ===


class AnswerNoteCreate(BaseModel):
    """답변 노트 생성 요청"""

    question_id: UUID = Field(description="질문 ID")
    initial_answer: str = Field(min_length=1, description="초기 답변")
    first_feedback: str | None = Field(default=None, description="첫 번째 피드백")
    second_feedback: str | None = Field(default=None, description="두 번째 피드백")
    final_answer: str | None = Field(default=None, description="최종 답변")


class AnswerNoteUpdate(BaseModel):
    """답변 노트 수정 요청"""

    first_feedback: str | None = Field(default=None, description="첫 번째 피드백")
    second_feedback: str | None = Field(default=None, description="두 번째 피드백")
    final_answer: str | None = Field(default=None, description="최종 답변")


class AnswerNoteResponse(BaseModel):
    """답변 노트 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    question_id: UUID
    initial_answer: str
    first_feedback: str | None
    second_feedback: str | None
    final_answer: str | None
    created_at: datetime
    updated_at: datetime


# === QA 히스토리 ===


class QAHistoryResponse(BaseModel):
    """QA 히스토리 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    question_id: UUID
    user_answer: str
    ai_model: str
    ai_response: str
    score: int
    hints: str
    created_at: datetime
