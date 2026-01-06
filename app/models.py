from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class JobType(str, Enum):
    """직무 타입 (확장 가능)"""
    MARKETING = "marketing"
    IT = "it"
    # 향후 추가 가능: SALES = "sales", HR = "hr", etc.


class Level(str, Enum):
    """레벨 (확장 가능)"""
    INTERN = "intern"
    ENTRY = "entry"
    EXPERIENCED = "experienced"
    # 향후 추가 가능: SENIOR = "senior", LEAD = "lead", etc.


class Question(SQLModel, table=True):
    """질문 모델 (공통/직무/외국인특화)"""

    __tablename__ = "questions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    question: str = Field(index=True)
    category: str = Field(index=True)  # 'common', 'job', 'foreigner'
    job_type: str | None = Field(default=None)  # JobType enum 값
    level: str | None = Field(default=None)  # Level enum 값
    model_answer: str
    reasoning: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # 관계
    interview_answers: list["InterviewAnswer"] = Relationship(back_populates="question")
    answer_notes: list["AnswerNote"] = Relationship(back_populates="question", cascade_delete=True)
    qa_history: list["QAHistory"] = Relationship(back_populates="question", cascade_delete=True)


class InterviewSet(SQLModel, table=True):
    """면접 세트 모델"""

    __tablename__ = "interview_sets"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(index=True)  # 유저 ID (JWT sub)
    job_type: str = Field(index=True)  # JobType enum 값
    level: str = Field(index=True)  # Level enum 값
    status: str = Field(default="in_progress")  # 'in_progress', 'completed'
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = Field(default=None)

    # 관계
    answers: list["InterviewAnswer"] = Relationship(back_populates="interview_set", cascade_delete=True)
    evaluations: list["InterviewEvaluation"] = Relationship(back_populates="interview_set", cascade_delete=True)


class InterviewAnswer(SQLModel, table=True):
    """면접 답변 모델 (꼬리질문 포함)"""

    __tablename__ = "interview_answers"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    set_id: UUID = Field(foreign_key="interview_sets.id", index=True)
    question_id: UUID = Field(foreign_key="questions.id", index=True)
    question_order: int
    user_answer: str
    follow_up_question: str | None = Field(default=None)
    follow_up_answer: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # 관계
    interview_set: InterviewSet = Relationship(back_populates="answers")
    question: Question = Relationship(back_populates="interview_answers")


class InterviewEvaluation(SQLModel, table=True):
    """면접 평가 결과 모델"""

    __tablename__ = "interview_evaluations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    set_id: UUID = Field(foreign_key="interview_sets.id", index=True)
    logic: int  # 논리성 점수 (0-100)
    evidence: int  # 근거 점수 (0-100)
    job_understanding: int  # 직무이해도 (0-100)
    formality: int  # 한국어 격식 (0-100)
    completeness: int  # 완성도 (0-100)
    overall_feedback: str
    detailed_feedback: str  # JSON 형식
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # 관계
    interview_set: InterviewSet = Relationship(back_populates="evaluations")


class AnswerNote(SQLModel, table=True):
    """답변 노트 모델 (유저가 저장한 최종 답변)"""

    __tablename__ = "answer_notes"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(index=True)  # 유저 ID (JWT sub)
    question_id: UUID = Field(foreign_key="questions.id", index=True)
    initial_answer: str
    first_feedback: str | None = Field(default=None)
    second_feedback: str | None = Field(default=None)
    final_answer: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # 관계
    question: Question = Relationship(back_populates="answer_notes")


class QAHistory(SQLModel, table=True):
    """QA 히스토리 모델"""

    __tablename__ = "qa_history"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(index=True)  # 유저 ID (JWT sub)
    question_id: UUID = Field(foreign_key="questions.id", index=True)
    user_answer: str
    ai_model: str
    ai_response: str
    score: int  # 0-100
    hints: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # 관계
    question: Question = Relationship(back_populates="qa_history")
