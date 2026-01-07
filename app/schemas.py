from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import InterviewSetStatus, JobType, Level

# === 질문 ===


class QuestionCreate(BaseModel):
    """질문 생성 요청
    
    면접 질문을 생성합니다.
    category가 'job'인 경우 job_type을 함께 지정하는 것을 권장합니다.
    """

    question: str = Field(min_length=1, description="질문 내용 (예: '자기소개를 해주세요.')")
    category: str = Field(
        pattern="^(common|job|foreigner)$", 
        description="카테고리 (common: 공통, job: 직무별, foreigner: 외국인특화)"
    )
    job_type: JobType | None = Field(
        default=None, 
        description="직무 타입 (category가 job인 경우 권장, it/marketing)"
    )
    level: Level | None = Field(
        default=None, 
        description="경력 레벨 (intern: 인턴, entry: 신입, experienced: 경력)"
    )
    model_answer: str = Field(min_length=1, description="모범답안 (AI 평가 기준으로 사용)")
    reasoning: str = Field(min_length=1, description="모범답안의 논리와 이유 (왜 이 답변이 좋은지)")


class QuestionUpdate(QuestionCreate):
    """질문 수정 요청
    
    기존 질문의 모든 필드를 수정합니다 (PUT 방식).
    """

    pass


class QuestionResponse(BaseModel):
    """질문 응답
    
    질문의 전체 정보를 포함합니다.
    model_answer와 reasoning은 AI 평가 시 참고 기준으로 사용됩니다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="질문 고유 ID")
    question: str = Field(description="질문 내용")
    category: str = Field(description="카테고리 (common/job/foreigner)")
    job_type: str | None = Field(description="직무 타입 (it/marketing, category가 job인 경우)")
    level: str | None = Field(description="경력 레벨 (intern/entry/experienced)")
    model_answer: str = Field(description="모범답안")
    reasoning: str = Field(description="모범답안의 논리와 이유")
    created_at: datetime = Field(description="생성 일시")
    updated_at: datetime = Field(description="수정 일시")


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
    """면접 세트 생성 요청
    
    새로운 면접 세트를 생성합니다.
    질문은 공통 40%, 직무 30%, 외국인특화 30% 비율로 자동 선택됩니다.
    """

    title: str | None = Field(
        default=None, 
        min_length=1, 
        max_length=100, 
        description="면접 세트 제목 (미입력 시 자동 생성: 'IT ENTRY 면접 (2024-01-01)')"
    )
    job_type: JobType = Field(description="직무 타입 (it: IT/개발, marketing: 마케팅)")
    level: Level = Field(description="경력 레벨 (intern: 인턴, entry: 신입, experienced: 경력)")
    question_count: int = Field(
        default=3, 
        ge=1, 
        le=10, 
        description="질문 개수 (1~10개, 기본값 3개)"
    )


class QuestionInfo(BaseModel):
    """질문 정보 (면접 세트에 포함된 개별 질문)"""

    id: UUID = Field(description="질문 고유 ID")
    question: str = Field(description="질문 내용")
    order: int = Field(description="질문 순서 (1부터 시작)")
    category: str = Field(description="카테고리 (common: 공통, job: 직무, foreigner: 외국인특화)")


class InterviewSetCreateResponse(BaseModel):
    """면접 세트 생성 응답
    
    생성된 면접 세트의 ID와 배정된 질문 목록을 반환합니다.
    클라이언트는 이 질문 목록을 순서대로 사용자에게 보여주면 됩니다.
    """

    set_id: UUID = Field(description="생성된 면접 세트 ID")
    questions: list[QuestionInfo] = Field(description="배정된 질문 목록 (order 순서대로 정렬됨)")


class InterviewSetResponse(BaseModel):
    """면접 세트 응답
    
    면접 세트의 기본 정보를 담고 있습니다.
    status 필드로 현재 면접 진행 상태를 확인할 수 있습니다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="면접 세트 고유 ID")
    user_id: str = Field(description="사용자 ID (JWT sub)")
    title: str = Field(description="면접 세트 제목")
    job_type: str = Field(description="직무 타입 (it, marketing 등)")
    level: str = Field(description="레벨 (intern, entry, experienced)")
    status: InterviewSetStatus = Field(description="면접 상태: in_progress(면접중), pending_evaluation(평가대기), completed(평가완료)")
    created_at: datetime = Field(description="생성 일시")
    completed_at: datetime | None = Field(description="완료 일시 (평가 완료 시에만 값이 있음)")


class SubmitAnswerRequest(BaseModel):
    """답변 제출 요청
    
    면접 질문에 대한 사용자 답변을 제출합니다.
    user_answer 또는 audio 중 하나는 필수입니다.
    enable_follow_up을 true로 설정하면 AI가 압박 꼬리질문을 생성합니다.
    """

    set_id: UUID = Field(description="면접 세트 ID")
    question_id: UUID = Field(description="질문 ID (면접 세트 생성 시 반환된 값)")
    question_order: int = Field(ge=1, description="질문 순서 (1부터 시작, 면접 세트 생성 시 반환된 order 값)")
    user_answer: str | None = Field(default=None, min_length=1, description="사용자 답변 (텍스트)")
    audio: AudioInput | None = Field(default=None, description="음성 입력 (아직 미지원)")
    enable_follow_up: bool = Field(default=False, description="꼬리질문 생성 여부 (true면 AI가 압박 꼬리질문 생성)")
    ai_model: str | None = Field(default=None, description="AI 모델명 (미지정 시 기본 모델 사용)")


class SubmitAnswerResponse(BaseModel):
    """답변 제출 응답
    
    답변 저장 결과를 반환합니다.
    enable_follow_up이 true였으면 follow_up_question에 AI 생성 꼬리질문이 포함됩니다.
    """

    answer_id: UUID = Field(description="저장된 답변 ID (꼬리질문 답변 제출 시 사용)")
    follow_up_question: str | None = Field(description="AI가 생성한 꼬리질문 (없으면 null)")
    transcript: str | None = Field(description="음성 전사 텍스트 (음성 입력 시, 현재 미지원)")


class SubmitFollowUpRequest(BaseModel):
    """꼬리질문 답변 제출 요청
    
    AI가 생성한 꼬리질문에 대한 답변을 제출합니다.
    답변 제출 시 반환된 answer_id를 사용합니다.
    """

    answer_id: UUID = Field(description="답변 ID (답변 제출 시 반환된 answer_id)")
    follow_up_answer: str | None = Field(
        default=None, min_length=1, description="꼬리질문에 대한 답변 (텍스트)"
    )
    audio: AudioInput | None = Field(default=None, description="음성 입력 (아직 미지원)")


class SubmitFollowUpResponse(BaseModel):
    """꼬리질문 답변 제출 응답
    
    꼬리질문 답변 저장 결과를 반환합니다.
    모든 질문과 꼬리질문 답변이 완료되면 면접 세트 상태가 pending_evaluation으로 자동 전환됩니다.
    """

    success: bool = Field(description="저장 성공 여부")
    transcript: str | None = Field(description="음성 전사 텍스트 (음성 입력 시, 현재 미지원)")


class InterviewAnswerResponse(BaseModel):
    """면접 답변 응답
    
    개별 질문에 대한 사용자 답변 정보입니다.
    꼬리질문이 있었다면 follow_up_question과 follow_up_answer도 포함됩니다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="답변 고유 ID")
    set_id: UUID = Field(description="면접 세트 ID")
    question_id: UUID = Field(description="질문 ID")
    question_order: int = Field(description="질문 순서")
    user_answer: str = Field(description="사용자 답변")
    follow_up_question: str | None = Field(description="AI 생성 꼬리질문 (없으면 null)")
    follow_up_answer: str | None = Field(description="꼬리질문에 대한 사용자 답변 (없으면 null)")
    created_at: datetime = Field(description="답변 생성 일시")
    question: QuestionResponse | None = Field(default=None, description="질문 상세 정보")


class DetailedFeedbackItem(BaseModel):
    """상세 피드백 항목
    
    개별 질문에 대한 AI 평가 피드백입니다.
    질문/답변 원문과 함께 AI의 피드백과 개선 제안이 포함됩니다.
    """

    question_order: int = Field(description="질문 순서")
    question_id: UUID | None = Field(default=None, description="질문 ID")
    question: str = Field(description="질문 내용")
    user_answer: str = Field(description="사용자 답변")
    follow_up_question: str | None = Field(default=None, description="꼬리질문 (없으면 null)")
    follow_up_answer: str | None = Field(default=None, description="꼬리질문 답변 (없으면 null)")
    feedback: str = Field(description="AI의 상세 피드백")
    improvements: str = Field(description="AI의 개선 제안")


class InterviewEvaluationResponse(BaseModel):
    """면접 평가 응답
    
    AI가 생성한 면접 종합 평가 결과입니다.
    5가지 항목 점수(0-100)와 종합 피드백, 질문별 상세 피드백을 포함합니다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="평가 고유 ID")
    set_id: UUID = Field(description="면접 세트 ID")
    logic: int = Field(ge=0, le=100, description="논리성 점수 (0-100): 답변의 논리적 구조와 일관성")
    evidence: int = Field(ge=0, le=100, description="근거 점수 (0-100): 구체적인 사례와 근거 제시")
    job_understanding: int = Field(ge=0, le=100, description="직무이해도 점수 (0-100): 지원 직무에 대한 이해도")
    formality: int = Field(ge=0, le=100, description="한국어 격식 점수 (0-100): 비즈니스 한국어 사용 적절성")
    completeness: int = Field(ge=0, le=100, description="완성도 점수 (0-100): 답변의 완성도와 충실성")
    overall_feedback: str = Field(description="AI의 종합 피드백")
    detailed_feedback: list[DetailedFeedbackItem] = Field(description="질문별 상세 피드백 목록")
    created_at: datetime = Field(description="평가 생성 일시")


class InterviewSetDetailResponse(BaseModel):
    """면접 세트 상세 응답
    
    면접 세트의 전체 정보를 조회합니다.
    questions로 원래 배정된 질문 목록을, answers로 제출된 답변들을 확인할 수 있습니다.
    next_question_order를 사용하면 중단된 면접을 이어서 진행할 수 있습니다.
    """

    set: InterviewSetResponse = Field(description="면접 세트 기본 정보")
    questions: list[QuestionInfo] = Field(default_factory=list, description="면접 세트에 배정된 질문 목록 (이어하기 시 이 목록 사용)")
    answers: list[InterviewAnswerResponse] = Field(description="제출된 답변 목록")
    evaluation: InterviewEvaluationResponse | None = Field(description="AI 평가 결과 (평가 완료 시에만 값이 있음)")
    next_question_order: int | None = Field(default=None, description="다음에 답할 질문 순서 (모든 답변 완료 시 null)")


# === 답변 노트 ===


class AnswerNoteCreate(BaseModel):
    """답변 노트 생성 요청
    
    특정 질문에 대한 답변 연습 노트를 생성합니다.
    처음에는 initial_answer만 작성하고, 나중에 피드백과 최종 답변을 추가할 수 있습니다.
    """

    question_id: UUID = Field(description="연결할 질문 ID")
    initial_answer: str = Field(min_length=1, description="처음 작성한 답변 (필수)")
    first_feedback: str | None = Field(default=None, description="첫 번째 피드백 (선택)")
    second_feedback: str | None = Field(default=None, description="두 번째 피드백 (선택)")
    final_answer: str | None = Field(default=None, description="최종 정리된 답변 (선택)")


class AnswerNoteUpdate(BaseModel):
    """답변 노트 수정 요청
    
    기존 답변 노트의 피드백과 최종 답변을 수정합니다.
    전송한 필드만 업데이트됩니다 (PATCH 방식 동작).
    """

    first_feedback: str | None = Field(default=None, description="첫 번째 피드백 (전송 시 업데이트)")
    second_feedback: str | None = Field(default=None, description="두 번째 피드백 (전송 시 업데이트)")
    final_answer: str | None = Field(default=None, description="최종 정리된 답변 (전송 시 업데이트)")


class AnswerNoteResponse(BaseModel):
    """답변 노트 응답
    
    사용자가 저장한 답변 연습 노트의 전체 정보입니다.
    initial_answer → first_feedback → second_feedback → final_answer 순으로 답변을 개선해나가는 용도입니다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="답변 노트 고유 ID")
    user_id: str = Field(description="작성자 ID")
    question_id: UUID = Field(description="연결된 질문 ID")
    initial_answer: str = Field(description="처음 작성한 답변")
    first_feedback: str | None = Field(description="첫 번째 피드백 (없으면 null)")
    second_feedback: str | None = Field(description="두 번째 피드백 (없으면 null)")
    final_answer: str | None = Field(description="최종 정리된 답변 (없으면 null)")
    created_at: datetime = Field(description="생성 일시")
    updated_at: datetime = Field(description="마지막 수정 일시")


# === QA 히스토리 ===


class QAHistoryResponse(BaseModel):
    """QA 히스토리 응답
    
    질문별 AI 평가 히스토리입니다.
    사용자가 특정 질문에 대해 답변하고 AI 평가를 받은 기록을 저장합니다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="히스토리 고유 ID")
    user_id: str = Field(description="사용자 ID")
    question_id: UUID = Field(description="질문 ID")
    user_answer: str = Field(description="사용자 답변")
    ai_model: str = Field(description="사용된 AI 모델명")
    ai_response: str = Field(description="AI 원본 응답")
    score: int = Field(ge=0, le=100, description="AI 평가 점수 (0-100)")
    hints: str = Field(description="AI가 제공한 힌트/피드백")
    created_at: datetime = Field(description="평가 일시")
