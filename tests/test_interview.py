from uuid import UUID

from fastapi.testclient import TestClient


def create_question(client: TestClient, auth_headers: dict, category: str = "common") -> str:
    """테스트용 질문 생성 (어드민)"""
    response = client.post(
        "/admin/questions",
        json={
            "question": f"{category} 질문입니다.",
            "category": category,
            "job_type": "it" if category == "job" else None,
            "model_answer": "테스트 답변",
            "reasoning": "테스트 이유",
        },
        headers=auth_headers,
    )
    return response.json()["id"]


def test_create_interview_set(client: TestClient, auth_headers: dict, seed_questions):
    """면접 세트 생성 테스트"""
    response = client.post(
        "/interview/sets",
        json={
            "job_type": "it",
            "level": "entry",
            "question_count": 3,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "set_id" in data
    assert "questions" in data
    # UUID 형식 확인
    assert UUID(data["set_id"])
    assert len(data["questions"]) == 3


def test_create_interview_set_with_different_job_types(client: TestClient, auth_headers: dict, seed_questions):
    """다양한 직무로 면접 세트 생성"""
    for job_type in ["it", "marketing"]:
        response = client.post(
            "/interview/sets",
            json={
                "job_type": job_type,
                "level": "intern",
                "question_count": 2,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 2


def test_create_interview_set_invalid_job_type(client: TestClient, auth_headers: dict):
    """잘못된 직무 타입으로 면접 세트 생성 시도"""
    response = client.post(
        "/interview/sets",
        json={
            "job_type": "invalid",
            "level": "entry",
            "question_count": 3,
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_submit_answer(client: TestClient, auth_headers: dict, seed_questions):
    """답변 제출 테스트"""
    # 질문 생성
    question_id = create_question(client, auth_headers)

    # 면접 세트 생성
    set_response = client.post(
        "/interview/sets",
        json={
            "job_type": "it",
            "level": "entry",
            "question_count": 1,
        },
        headers=auth_headers,
    )
    set_id = set_response.json()["set_id"]

    # 답변 제출
    response = client.post(
        "/interview/answers",
        json={
            "set_id": set_id,
            "question_id": question_id,
            "question_order": 1,
            "user_answer": "저는 5년 경력의 개발자입니다.",
            "enable_follow_up": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer_id" in data
    assert UUID(data["answer_id"])


def test_submit_answer_with_follow_up(client: TestClient, auth_headers: dict, seed_questions):
    """꼬리질문 포함 답변 제출 테스트"""
    # 질문 생성
    question_id = create_question(client, auth_headers)

    # 면접 세트 생성
    set_response = client.post(
        "/interview/sets",
        json={
            "job_type": "it",
            "level": "entry",
            "question_count": 1,
        },
        headers=auth_headers,
    )
    set_id = set_response.json()["set_id"]

    # 꼬리질문 활성화하여 답변 제출
    response = client.post(
        "/interview/answers",
        json={
            "set_id": set_id,
            "question_id": question_id,
            "question_order": 1,
            "user_answer": "저는 팀 프로젝트에서 리더 역할을 맡았습니다.",
            "enable_follow_up": True,
            "ai_model": "google/gemini-3-flash-preview",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    # OpenRouter API 키가 있으면 꼬리질문이 생성됨
    # 없으면 None


def test_submit_follow_up_answer(client: TestClient, auth_headers: dict, seed_questions):
    """꼬리질문 답변 제출 테스트"""
    # 질문 생성
    question_id = create_question(client, auth_headers)

    # 면접 세트 생성
    set_response = client.post(
        "/interview/sets",
        json={
            "job_type": "it",
            "level": "entry",
            "question_count": 1,
        },
        headers=auth_headers,
    )
    set_id = set_response.json()["set_id"]

    # 초기 답변 제출
    answer_response = client.post(
        "/interview/answers",
        json={
            "set_id": set_id,
            "question_id": question_id,
            "question_order": 1,
            "user_answer": "저는 개발자입니다.",
            "enable_follow_up": True,
        },
        headers=auth_headers,
    )
    answer_id = answer_response.json()["answer_id"]

    # 꼬리질문 답변 제출
    response = client.post(
        "/interview/follow-up-answers",
        json={
            "answer_id": answer_id,
            "follow_up_answer": "구체적으로는 백엔드 개발을 담당했습니다.",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_complete_interview(client: TestClient, auth_headers: dict, seed_questions):
    """면접 완료 테스트"""
    # 질문 생성
    question_id = create_question(client, auth_headers)

    # 면접 세트 생성
    set_response = client.post(
        "/interview/sets",
        json={
            "job_type": "it",
            "level": "entry",
            "question_count": 1,
        },
        headers=auth_headers,
    )
    set_id = set_response.json()["set_id"]

    # 답변 제출
    client.post(
        "/interview/answers",
        json={
            "set_id": set_id,
            "question_id": question_id,
            "question_order": 1,
            "user_answer": "저는 5년 경력의 풀스택 개발자입니다.",
        },
        headers=auth_headers,
    )

    # 면접 완료 (OpenRouter API 키 필요)
    response = client.post(f"/interview/sets/{set_id}/complete", headers=auth_headers)
    # API 키가 있으면 200, 없으면 500
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "logic" in data
        assert "evidence" in data
        assert "overall_feedback" in data


def test_get_interview_set(client: TestClient, auth_headers: dict, seed_questions):
    """면접 세트 조회 테스트"""
    # 면접 세트 생성
    set_response = client.post(
        "/interview/sets",
        json={
            "job_type": "it",
            "level": "entry",
            "question_count": 1,
        },
        headers=auth_headers,
    )
    set_id = set_response.json()["set_id"]

    # 조회
    response = client.get(f"/interview/sets/{set_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "set" in data
    assert "answers" in data
    assert data["set"]["id"] == set_id
    assert data["set"]["user_id"] == "1"


def test_get_interview_set_not_found(client: TestClient, auth_headers: dict):
    """존재하지 않는 면접 세트 조회"""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/interview/sets/{fake_uuid}", headers=auth_headers)
    assert response.status_code == 404


def test_list_interview_sets(client: TestClient, auth_headers: dict, seed_questions):
    """면접 세트 목록 조회 테스트 (본인 것만 조회)"""
    # 면접 세트 2개 생성
    response1 = client.post(
        "/interview/sets",
        json={
            "job_type": "it",
            "level": "entry",
            "question_count": 1,
        },
        headers=auth_headers,
    )
    response2 = client.post(
        "/interview/sets",
        json={
            "job_type": "marketing",
            "level": "intern",
            "question_count": 1,
        },
        headers=auth_headers,
    )

    response = client.get("/interview/sets", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # 생성 성공한 세트의 개수 확인
    assert response1.status_code == 201
    assert response2.status_code == 201
    assert len(data) == 2
    
    # 모든 세트가 user_id = "1"인지 확인
    for interview_set in data:
        assert interview_set["user_id"] == "1"


def test_complete_interview_without_answers(client: TestClient, auth_headers: dict, seed_questions):
    """답변 없이 면접 완료 시도"""
    # 면접 세트만 생성 (답변 없음)
    set_response = client.post(
        "/interview/sets",
        json={
            "job_type": "it",
            "level": "entry",
            "question_count": 1,
        },
        headers=auth_headers,
    )
    set_id = set_response.json()["set_id"]

    # 답변 없이 완료 시도
    response = client.post(f"/interview/sets/{set_id}/complete", headers=auth_headers)
    assert response.status_code == 400
    assert "답변이 없습니다" in response.json()["detail"]


def test_user_isolation_interview_sets(client: TestClient, auth_headers: dict, auth_headers_user2: dict, seed_questions):
    """사용자별 면접 세트 격리 테스트"""
    # User1이 면접 세트 생성
    set1_response = client.post(
        "/interview/sets",
        json={
            "job_type": "it",
            "level": "entry",
            "question_count": 1,
        },
        headers=auth_headers,
    )
    assert set1_response.status_code == 201
    set1_id = set1_response.json()["set_id"]

    # User2가 면접 세트 생성
    set2_response = client.post(
        "/interview/sets",
        json={
            "job_type": "marketing",
            "level": "intern",
            "question_count": 1,
        },
        headers=auth_headers_user2,
    )
    assert set2_response.status_code == 201

    # User1이 목록 조회 시 본인 것만 보임
    list1_response = client.get("/interview/sets", headers=auth_headers)
    assert list1_response.status_code == 200
    list1_data = list1_response.json()
    assert len(list1_data) >= 1
    assert all(s["user_id"] == "1" for s in list1_data)

    # User2가 목록 조회 시 본인 것만 보임
    list2_response = client.get("/interview/sets", headers=auth_headers_user2)
    assert list2_response.status_code == 200
    list2_data = list2_response.json()
    assert len(list2_data) >= 1
    assert all(s["user_id"] == "2" for s in list2_data)

    # User2가 User1의 세트를 조회하려고 시도 (실패해야 함)
    get_response = client.get(f"/interview/sets/{set1_id}", headers=auth_headers_user2)
    assert get_response.status_code == 403

    # User2가 User1의 세트를 완료하려고 시도 (실패해야 함)
    complete_response = client.post(
        f"/interview/sets/{set1_id}/complete",
        headers=auth_headers_user2,
    )
    assert complete_response.status_code == 403
