from uuid import UUID

from fastapi.testclient import TestClient


def create_question(client: TestClient, auth_headers: dict) -> str:
    """테스트용 질문 생성 (어드민)"""
    response = client.post(
        "/admin/questions",
        json={
            "question": "자기소개를 해주세요.",
            "category": "common",
            "model_answer": "저는...",
            "reasoning": "자기소개는...",
        },
        headers=auth_headers,
    )
    return response.json()["id"]


def test_create_answer_note(client: TestClient, auth_headers: dict):
    """답변 노트 생성 테스트"""
    question_id = create_question(client, auth_headers)

    response = client.post(
        "/answer-notes",
        json={
            "question_id": question_id,
            "initial_answer": "첫 번째 답변입니다.",
            "first_feedback": "피드백 1",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["initial_answer"] == "첫 번째 답변입니다."
    assert data["first_feedback"] == "피드백 1"
    assert data["user_id"] == "1"
    assert "id" in data
    # UUID 형식 확인
    assert UUID(data["id"])


def test_create_answer_note_minimal(client: TestClient, auth_headers: dict):
    """최소 정보로 답변 노트 생성"""
    question_id = create_question(client, auth_headers)

    response = client.post(
        "/answer-notes",
        json={
            "question_id": question_id,
            "initial_answer": "답변",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["initial_answer"] == "답변"
    assert data["first_feedback"] is None
    assert data["final_answer"] is None


def test_create_answer_note_complete(client: TestClient, auth_headers: dict):
    """모든 필드 포함 답변 노트 생성"""
    question_id = create_question(client, auth_headers)

    response = client.post(
        "/answer-notes",
        json={
            "question_id": question_id,
            "initial_answer": "초기 답변",
            "first_feedback": "첫 번째 피드백",
            "second_feedback": "두 번째 피드백",
            "final_answer": "최종 답변",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["initial_answer"] == "초기 답변"
    assert data["first_feedback"] == "첫 번째 피드백"
    assert data["second_feedback"] == "두 번째 피드백"
    assert data["final_answer"] == "최종 답변"


def test_list_answer_notes(client: TestClient, auth_headers: dict):
    """답변 노트 목록 조회 테스트 (본인 것만 조회)"""
    question_id = create_question(client, auth_headers)

    # 답변 노트 2개 생성
    client.post(
        "/answer-notes",
        json={
            "question_id": question_id,
            "initial_answer": "답변 1",
        },
        headers=auth_headers,
    )
    client.post(
        "/answer-notes",
        json={
            "question_id": question_id,
            "initial_answer": "답변 2",
        },
        headers=auth_headers,
    )

    response = client.get("/answer-notes", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # 모든 노트가 user_id = "1"인지 확인
    for note in data:
        assert note["user_id"] == "1"


def test_update_answer_note(client: TestClient, auth_headers: dict):
    """답변 노트 수정 테스트"""
    question_id = create_question(client, auth_headers)

    # 답변 노트 생성
    create_response = client.post(
        "/answer-notes",
        json={
            "question_id": question_id,
            "initial_answer": "원래 답변",
        },
        headers=auth_headers,
    )
    note_id = create_response.json()["id"]

    # 수정
    response = client.put(
        f"/answer-notes/{note_id}",
        json={
            "first_feedback": "첫 번째 피드백",
            "final_answer": "최종 답변",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_feedback"] == "첫 번째 피드백"
    assert data["final_answer"] == "최종 답변"
    assert data["initial_answer"] == "원래 답변"  # 변경되지 않음


def test_update_answer_note_partial(client: TestClient, auth_headers: dict):
    """답변 노트 부분 수정 테스트"""
    question_id = create_question(client, auth_headers)

    # 답변 노트 생성
    create_response = client.post(
        "/answer-notes",
        json={
            "question_id": question_id,
            "initial_answer": "답변",
            "first_feedback": "피드백 1",
        },
        headers=auth_headers,
    )
    note_id = create_response.json()["id"]

    # second_feedback만 추가
    response = client.put(
        f"/answer-notes/{note_id}",
        json={
            "second_feedback": "피드백 2",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_feedback"] == "피드백 1"  # 기존 값 유지
    assert data["second_feedback"] == "피드백 2"


def test_update_answer_note_not_found(client: TestClient, auth_headers: dict):
    """존재하지 않는 답변 노트 수정 시도"""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = client.put(
        f"/answer-notes/{fake_uuid}",
        json={
            "final_answer": "최종 답변",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_answer_note(client: TestClient, auth_headers: dict):
    """답변 노트 삭제 테스트"""
    question_id = create_question(client, auth_headers)

    # 답변 노트 생성
    create_response = client.post(
        "/answer-notes",
        json={
            "question_id": question_id,
            "initial_answer": "답변",
        },
        headers=auth_headers,
    )
    note_id = create_response.json()["id"]

    # 삭제
    response = client.delete(f"/answer-notes/{note_id}", headers=auth_headers)
    assert response.status_code == 204

    # 삭제 후 목록에서 확인 (삭제된 노트는 없어야 함)
    list_response = client.get("/answer-notes", headers=auth_headers)
    note_ids = [note["id"] for note in list_response.json()]
    assert note_id not in note_ids


def test_delete_answer_note_not_found(client: TestClient, auth_headers: dict):
    """존재하지 않는 답변 노트 삭제 시도"""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = client.delete(f"/answer-notes/{fake_uuid}", headers=auth_headers)
    assert response.status_code == 404


def test_answer_note_workflow(client: TestClient, auth_headers: dict):
    """답변 노트 전체 워크플로우 테스트"""
    # 1. 질문 생성
    question_id = create_question(client, auth_headers)

    # 2. 초기 답변 작성
    create_response = client.post(
        "/answer-notes",
        json={
            "question_id": question_id,
            "initial_answer": "저는 3년 경력의 개발자입니다.",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    note_id = create_response.json()["id"]

    # 3. 첫 번째 피드백 추가
    update1_response = client.put(
        f"/answer-notes/{note_id}",
        json={
            "first_feedback": "더 구체적인 프로젝트 경험을 추가하세요.",
        },
        headers=auth_headers,
    )
    assert update1_response.status_code == 200

    # 4. 두 번째 피드백 추가
    update2_response = client.put(
        f"/answer-notes/{note_id}",
        json={
            "second_feedback": "수치와 결과를 포함하세요.",
        },
        headers=auth_headers,
    )
    assert update2_response.status_code == 200

    # 5. 최종 답변 작성
    final_response = client.put(
        f"/answer-notes/{note_id}",
        json={
            "final_answer": "저는 3년 경력의 백엔드 개발자입니다. 최근 프로젝트에서 API 응답 속도를 30% 향상시켰습니다.",
        },
        headers=auth_headers,
    )
    assert final_response.status_code == 200
    final_data = final_response.json()
    assert final_data["initial_answer"] == "저는 3년 경력의 개발자입니다."
    assert final_data["first_feedback"] == "더 구체적인 프로젝트 경험을 추가하세요."
    assert final_data["second_feedback"] == "수치와 결과를 포함하세요."
    assert "API 응답 속도" in final_data["final_answer"]


def test_user_isolation_answer_notes(client: TestClient, auth_headers: dict, auth_headers_user2: dict):
    """사용자별 답변 노트 격리 테스트"""
    # User1의 질문 생성
    question_id = create_question(client, auth_headers)

    # User1이 답변 노트 생성
    note1_response = client.post(
        "/answer-notes",
        json={
            "question_id": question_id,
            "initial_answer": "User1의 답변",
        },
        headers=auth_headers,
    )
    assert note1_response.status_code == 201
    note1_id = note1_response.json()["id"]

    # User2가 답변 노트 생성
    note2_response = client.post(
        "/answer-notes",
        json={
            "question_id": question_id,
            "initial_answer": "User2의 답변",
        },
        headers=auth_headers_user2,
    )
    assert note2_response.status_code == 201

    # User1이 목록 조회 시 본인 것만 보임
    list1_response = client.get("/answer-notes", headers=auth_headers)
    assert list1_response.status_code == 200
    list1_data = list1_response.json()
    assert len(list1_data) == 1
    assert list1_data[0]["initial_answer"] == "User1의 답변"
    assert list1_data[0]["user_id"] == "1"

    # User2가 목록 조회 시 본인 것만 보임
    list2_response = client.get("/answer-notes", headers=auth_headers_user2)
    assert list2_response.status_code == 200
    list2_data = list2_response.json()
    assert len(list2_data) == 1
    assert list2_data[0]["initial_answer"] == "User2의 답변"
    assert list2_data[0]["user_id"] == "2"

    # User2가 User1의 노트를 수정하려고 시도 (실패해야 함)
    update_response = client.put(
        f"/answer-notes/{note1_id}",
        json={"final_answer": "해킹 시도"},
        headers=auth_headers_user2,
    )
    assert update_response.status_code == 403

    # User2가 User1의 노트를 삭제하려고 시도 (실패해야 함)
    delete_response = client.delete(
        f"/answer-notes/{note1_id}",
        headers=auth_headers_user2,
    )
    assert delete_response.status_code == 403
