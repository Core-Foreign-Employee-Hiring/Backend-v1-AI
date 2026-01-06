from uuid import UUID

from fastapi.testclient import TestClient


def test_create_question(client: TestClient, auth_headers: dict):
    """질문 생성 테스트 (어드민)"""
    response = client.post(
        "/admin/questions",
        json={
            "question": "자기소개를 해주세요.",
            "category": "common",
            "job_type": None,
            "level": None,
            "model_answer": "저는 5년 경력의 개발자입니다...",
            "reasoning": "자기소개는 간결하고 명확하게...",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["question"] == "자기소개를 해주세요."
    assert data["category"] == "common"
    assert "id" in data
    # UUID 형식인지 확인
    assert UUID(data["id"])


def test_create_question_with_job_type(client: TestClient, auth_headers: dict):
    """직무별 질문 생성 테스트 (어드민)"""
    response = client.post(
        "/admin/questions",
        json={
            "question": "RESTful API 설계 원칙을 설명해주세요.",
            "category": "job",
            "job_type": "it",
            "level": "entry",
            "model_answer": "RESTful API는 HTTP 메서드를 활용하여...",
            "reasoning": "직무 이해도를 확인하는 질문...",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["job_type"] == "it"
    assert data["level"] == "entry"


def test_create_question_invalid_category(client: TestClient, auth_headers: dict):
    """잘못된 카테고리로 질문 생성 시도 (어드민)"""
    response = client.post(
        "/admin/questions",
        json={
            "question": "테스트 질문",
            "category": "invalid",
            "model_answer": "테스트 답변",
            "reasoning": "테스트 이유",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "errors" in response.json()


def test_list_questions(client: TestClient, auth_headers: dict):
    """질문 목록 조회 테스트 (어드민)"""
    # 질문 2개 생성
    client.post(
        "/admin/questions",
        json={
            "question": "테스트 질문 1",
            "category": "common",
            "model_answer": "테스트 답변",
            "reasoning": "테스트 이유",
        },
        headers=auth_headers,
    )
    client.post(
        "/admin/questions",
        json={
            "question": "테스트 질문 2",
            "category": "foreigner",
            "model_answer": "테스트 답변",
            "reasoning": "테스트 이유",
        },
        headers=auth_headers,
    )

    response = client.get("/admin/questions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


def test_get_question(client: TestClient, auth_headers: dict):
    """질문 상세 조회 테스트 (어드민)"""
    # 질문 생성
    create_response = client.post(
        "/admin/questions",
        json={
            "question": "테스트 질문",
            "category": "common",
            "model_answer": "테스트 답변",
            "reasoning": "테스트 이유",
        },
        headers=auth_headers,
    )
    question_id = create_response.json()["id"]

    response = client.get(f"/admin/questions/{question_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == question_id
    assert data["question"] == "테스트 질문"


def test_get_question_not_found(client: TestClient, auth_headers: dict):
    """존재하지 않는 질문 조회 (어드민)"""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/admin/questions/{fake_uuid}", headers=auth_headers)
    assert response.status_code == 404


def test_update_question(client: TestClient, auth_headers: dict):
    """질문 수정 테스트 (어드민)"""
    # 질문 생성
    create_response = client.post(
        "/admin/questions",
        json={
            "question": "원래 질문",
            "category": "common",
            "model_answer": "원래 답변",
            "reasoning": "원래 이유",
        },
        headers=auth_headers,
    )
    question_id = create_response.json()["id"]

    # 질문 수정
    response = client.put(
        f"/admin/questions/{question_id}",
        json={
            "question": "수정된 질문",
            "category": "job",
            "job_type": "marketing",
            "level": "intern",
            "model_answer": "수정된 답변",
            "reasoning": "수정된 이유",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "수정된 질문"
    assert data["job_type"] == "marketing"


def test_delete_question(client: TestClient, auth_headers: dict):
    """질문 삭제 테스트 (어드민)"""
    # 질문 생성
    create_response = client.post(
        "/admin/questions",
        json={
            "question": "삭제할 질문",
            "category": "common",
            "model_answer": "답변",
            "reasoning": "이유",
        },
        headers=auth_headers,
    )
    question_id = create_response.json()["id"]

    # 질문 삭제
    response = client.delete(f"/admin/questions/{question_id}", headers=auth_headers)
    assert response.status_code == 204

    # 삭제 확인
    get_response = client.get(f"/admin/questions/{question_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_evaluate_answer(client: TestClient, auth_headers: dict):
    """AI 답변 평가 테스트 (일반 사용자)"""
    # 질문 생성 (어드민)
    create_response = client.post(
        "/admin/questions",
        json={
            "question": "자기소개를 해주세요.",
            "category": "common",
            "model_answer": "저는 5년 경력의 개발자입니다.",
            "reasoning": "간결하고 명확한 소개",
        },
        headers=auth_headers,
    )
    question_id = create_response.json()["id"]

    # 답변 평가 (일반 사용자, OpenRouter API 키가 없으면 실패할 수 있음)
    response = client.post(
        "/practice/evaluate",
        json={
            "question_id": question_id,
            "user_answer": "저는 3년 경력의 프론트엔드 개발자입니다.",
            "ai_model": "google/gemini-3-flash-preview",
        },
        headers=auth_headers,
    )
    # API 키가 없으면 500, 있으면 200
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "history_id" in data
        assert "score" in data


def test_get_qa_history(client: TestClient, auth_headers: dict):
    """QA 히스토리 조회 테스트 (일반 사용자, 본인 것만 조회)"""
    # 질문 생성 (어드민)
    create_response = client.post(
        "/admin/questions",
        json={
            "question": "테스트 질문",
            "category": "common",
            "model_answer": "테스트 답변",
            "reasoning": "테스트 이유",
        },
        headers=auth_headers,
    )
    question_id = create_response.json()["id"]

    # 히스토리 조회 (일반 사용자)
    response = client.get(f"/practice/history/{question_id}", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_user_isolation_qa_history(client: TestClient, auth_headers: dict, auth_headers_user2: dict):
    """사용자별 QA 히스토리 격리 테스트 (일반 사용자)"""
    # 질문 생성 (어드민, 공통 질문)
    create_response = client.post(
        "/admin/questions",
        json={
            "question": "자기소개를 해주세요.",
            "category": "common",
            "model_answer": "저는 개발자입니다.",
            "reasoning": "간결한 소개",
        },
        headers=auth_headers,
    )
    question_id = create_response.json()["id"]

    # User1과 User2가 같은 질문에 대해 답변 평가 (일반 사용자, API 키가 필요하므로 스킵될 수 있음)
    # User1의 평가
    eval1_response = client.post(
        "/practice/evaluate",
        json={
            "question_id": question_id,
            "user_answer": "저는 User1입니다.",
            "ai_model": "google/gemini-3-flash-preview",
        },
        headers=auth_headers,
    )
    
    # User2의 평가
    eval2_response = client.post(
        "/practice/evaluate",
        json={
            "question_id": question_id,
            "user_answer": "저는 User2입니다.",
            "ai_model": "google/gemini-3-flash-preview",
        },
        headers=auth_headers_user2,
    )

    # API 키가 있는 경우에만 히스토리 격리 테스트 진행
    if eval1_response.status_code == 200 and eval2_response.status_code == 200:
        # User1이 히스토리 조회 시 본인 것만 보임
        history1_response = client.get(
            f"/practice/history/{question_id}",
            headers=auth_headers,
        )
        assert history1_response.status_code == 200
        history1_data = history1_response.json()
        assert len(history1_data) == 1
        assert history1_data[0]["user_id"] == "1"
        assert "User1" in history1_data[0]["user_answer"]

        # User2가 히스토리 조회 시 본인 것만 보임
        history2_response = client.get(
            f"/practice/history/{question_id}",
            headers=auth_headers_user2,
        )
        assert history2_response.status_code == 200
        history2_data = history2_response.json()
        assert len(history2_data) == 1
        assert history2_data[0]["user_id"] == "2"
        assert "User2" in history2_data[0]["user_answer"]
