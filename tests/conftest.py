import os
import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.config import settings
from app.main import app


@pytest.fixture(name="session")
def session_fixture():
    """테스트용 데이터베이스 세션"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """테스트용 FastAPI 클라이언트"""

    def get_session_override():
        return session

    app.dependency_overrides[get_db] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_token():
    """테스트용 인증 토큰 생성 (user_id = '1')"""
    payload = {
        "sub": "1",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS512")
    return token


@pytest.fixture
def auth_token_user2():
    """테스트용 인증 토큰 생성 (user_id = '2')"""
    payload = {
        "sub": "2",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS512")
    return token


@pytest.fixture
def auth_headers(auth_token):
    """테스트용 인증 헤더"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def auth_headers_user2(auth_token_user2):
    """테스트용 인증 헤더 (user2)"""
    return {"Authorization": f"Bearer {auth_token_user2}"}


@pytest.fixture
def seed_questions(client, auth_headers):
    """테스트용 질문 데이터 생성 (면접 세트 생성에 필요)"""
    questions = []
    
    # 공통 질문 5개
    for i in range(5):
        response = client.post(
            "/admin/questions",
            json={
                "question": f"공통 질문 {i+1}",
                "category": "common",
                "model_answer": f"공통 답변 {i+1}",
                "reasoning": f"공통 이유 {i+1}",
            },
            headers=auth_headers,
        )
        if response.status_code == 201:
            questions.append(response.json())
    
    # IT 직무 질문 5개
    for i in range(5):
        response = client.post(
            "/admin/questions",
            json={
                "question": f"IT 직무 질문 {i+1}",
                "category": "job",
                "job_type": "it",
                "level": "entry",
                "model_answer": f"IT 답변 {i+1}",
                "reasoning": f"IT 이유 {i+1}",
            },
            headers=auth_headers,
        )
        if response.status_code == 201:
            questions.append(response.json())
    
    # 마케팅 직무 질문 5개
    for i in range(5):
        response = client.post(
            "/admin/questions",
            json={
                "question": f"마케팅 직무 질문 {i+1}",
                "category": "job",
                "job_type": "marketing",
                "level": "intern",
                "model_answer": f"마케팅 답변 {i+1}",
                "reasoning": f"마케팅 이유 {i+1}",
            },
            headers=auth_headers,
        )
        if response.status_code == 201:
            questions.append(response.json())
    
    # 외국인특화 질문 5개
    for i in range(5):
        response = client.post(
            "/admin/questions",
            json={
                "question": f"외국인특화 질문 {i+1}",
                "category": "foreigner",
                "model_answer": f"외국인특화 답변 {i+1}",
                "reasoning": f"외국인특화 이유 {i+1}",
            },
            headers=auth_headers,
        )
        if response.status_code == 201:
            questions.append(response.json())
    
    return questions


@pytest.fixture(scope="session", autouse=True)
def load_env():
    """테스트 실행 전 환경 변수 로드"""
    from dotenv import load_dotenv
    load_dotenv()


def pytest_configure(config):
    """pytest 설정 커스터마이징"""
    # API 키 상태 출력
    has_key = bool(os.getenv("OPENROUTER_API_KEY"))
    config._metadata = {
        "OpenRouter API Key": "✅ 설정됨" if has_key else "❌ 없음 (AI 테스트 스킵)"
    }


def pytest_collection_modifyitems(config, items):
    """테스트 수집 후 설정 수정"""
    # AI 테스트에 마커 추가
    for item in items:
        if "test_ai_integration" in str(item.fspath):
            item.add_marker(pytest.mark.ai)
            item.add_marker(pytest.mark.integration)
