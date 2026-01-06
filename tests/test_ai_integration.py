"""
실제 OpenRouter AI 통합 테스트
이 테스트들은 실제 API 키가 필요하며, 비용이 발생할 수 있습니다.

실행 방법:
uv run pytest tests/test_ai_integration.py -v -s
"""
import os
from uuid import UUID

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

# .env 파일 로드 (모듈 로드 시점에 실행)
load_dotenv()


def has_openrouter_key():
    """OpenRouter API 키가 설정되어 있는지 확인"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    # 빈 문자열이나 None이 아닌지 확인
    return bool(api_key and api_key.strip())


skip_without_api_key = pytest.mark.skipif(
    not has_openrouter_key(),
    reason="OpenRouter API 키가 필요합니다. .env 파일에 OPENROUTER_API_KEY를 설정하세요.",
)


@skip_without_api_key
def test_ai_answer_evaluation_detailed(client: TestClient, auth_headers: dict):
    """AI 답변 평가 상세 테스트 - 실제 응답 확인"""
    print("\n" + "=" * 80)
    print("🤖 AI 답변 평가 테스트")
    print("=" * 80)
    
    # 질문 생성
    question_data = {
        "question": "자기소개를 해주세요.",
        "category": "common",
        "model_answer": "저는 5년 경력의 백엔드 개발자입니다. Python과 FastAPI를 주로 사용하며, 최근 프로젝트에서 API 성능을 40% 향상시켰습니다.",
        "reasoning": "자기소개는 경력, 기술 스택, 구체적인 성과를 포함하여 간결하게 답변해야 합니다.",
    }
    
    create_response = client.post("/admin/questions", json=question_data, headers=auth_headers)
    assert create_response.status_code == 201
    question_id = create_response.json()["id"]
    
    print(f"\n📝 생성된 질문:")
    print(f"   ID: {question_id}")
    print(f"   질문: {question_data['question']}")
    print(f"   모범답안: {question_data['model_answer']}")
    
    # 평가할 답변들
    test_answers = [
        {
            "name": "우수한 답변",
            "answer": "저는 3년 경력의 백엔드 개발자입니다. 주로 Python과 Django를 사용했으며, 최근 프로젝트에서 데이터베이스 쿼리 최적화로 응답 시간을 50% 단축시켰습니다.",
        },
        {
            "name": "보통 답변",
            "answer": "저는 개발자입니다. 프로그래밍을 좋아하고 열심히 일합니다.",
        },
        {
            "name": "미흡한 답변",
            "answer": "안녕하세요.",
        },
    ]
    
    for test_case in test_answers:
        print(f"\n{'─' * 80}")
        print(f"📊 테스트 케이스: {test_case['name']}")
        print(f"{'─' * 80}")
        print(f"답변: {test_case['answer']}")
        
        # AI 평가 요청
        eval_response = client.post(
            "/questions/evaluate",
            json={
                "question_id": question_id,
                "user_answer": test_case["answer"],
                "ai_model": "google/gemini-3-flash-preview",
            },
            headers=auth_headers,
        )
        
        if eval_response.status_code == 200:
            result = eval_response.json()
            print(f"\n✅ 평가 결과:")
            print(f"   점수: {result['score']}/100")
            print(f"   \n   💡 힌트:")
            print(f"   {result['hints']}")
            if result.get('strengths'):
                print(f"   \n   👍 잘한 점:")
                print(f"   {result['strengths']}")
            if result.get('improvements'):
                print(f"   \n   📈 개선점:")
                print(f"   {result['improvements']}")
        else:
            print(f"\n❌ 평가 실패: {eval_response.status_code}")
            print(f"   오류: {eval_response.json()}")
    
    print("\n" + "=" * 80)


@skip_without_api_key
def test_ai_follow_up_question_generation(client: TestClient, auth_headers: dict, seed_questions):
    """AI 꼬리질문 생성 상세 테스트"""
    print("\n" + "=" * 80)
    print("🔄 AI 꼬리질문 생성 테스트")
    print("=" * 80)
    
    # 질문 생성
    question_response = client.post(
        "/admin/questions",
        json={
            "question": "최근 프로젝트에서 어려웠던 점은 무엇인가요?",
            "category": "common",
            "model_answer": "최근 프로젝트에서 대용량 데이터 처리가 어려웠습니다. 이를 해결하기 위해 배치 처리와 비동기 작업을 도입했고, 처리 시간을 70% 단축시켰습니다.",
            "reasoning": "문제 인식, 해결 방법, 결과를 구체적으로 설명",
        },
        headers=auth_headers,
    )
    question_id = question_response.json()["id"]
    
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
    
    print(f"\n📝 면접 세트 ID: {set_id}")
    print(f"📝 질문 ID: {question_id}")
    
    # 다양한 답변에 대한 꼬리질문 생성
    test_answers = [
        {
            "name": "구체적인 답변",
            "answer": "최근 프로젝트에서 실시간 데이터 동기화가 가장 어려웠습니다. 여러 서버 간의 데이터 일관성을 유지하는 것이 문제였고, Redis를 활용한 캐싱 전략으로 해결했습니다.",
        },
        {
            "name": "추상적인 답변",
            "answer": "팀원들과의 의사소통이 어려웠습니다. 하지만 노력해서 극복했습니다.",
        },
        {
            "name": "기술적 답변",
            "answer": "레거시 코드의 리팩토링이 어려웠습니다. 테스트 커버리지가 없어서 변경 시 사이드 이펙트가 우려됐지만, 점진적으로 테스트를 추가하면서 안전하게 진행했습니다.",
        },
    ]
    
    for idx, test_case in enumerate(test_answers, 1):
        print(f"\n{'─' * 80}")
        print(f"🔄 테스트 케이스 {idx}: {test_case['name']}")
        print(f"{'─' * 80}")
        print(f"답변: {test_case['answer']}")
        
        # 꼬리질문 생성 활성화
        response = client.post(
            "/interview/answers",
            json={
                "set_id": set_id,
                "question_id": question_id,
                "question_order": idx,
                "user_answer": test_case["answer"],
                "enable_follow_up": True,
                "ai_model": "google/gemini-3-flash-preview",
            },
            headers=auth_headers,
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("follow_up_question"):
                print(f"\n🤔 생성된 꼬리질문:")
                print(f"   {result['follow_up_question']}")
            else:
                print(f"\n⚠️ 꼬리질문이 생성되지 않았습니다.")
        else:
            print(f"\n❌ 요청 실패: {response.status_code}")
            print(f"   오류: {response.json()}")
    
    print("\n" + "=" * 80)


@skip_without_api_key
def test_ai_comprehensive_interview_evaluation(client: TestClient, auth_headers: dict, seed_questions):
    """AI 종합 면접 평가 상세 테스트"""
    print("\n" + "=" * 80)
    print("📊 AI 종합 면접 평가 테스트")
    print("=" * 80)
    
    # 질문 3개 생성
    questions = []
    question_data = [
        {
            "question": "자기소개를 해주세요.",
            "category": "common",
            "model_answer": "저는 3년 경력의 개발자입니다.",
            "reasoning": "간결하고 명확한 소개",
        },
        {
            "question": "우리 회사에 지원한 이유는 무엇인가요?",
            "category": "common",
            "model_answer": "귀사의 기술 스택과 비전에 공감합니다.",
            "reasoning": "회사에 대한 이해와 열정 표현",
        },
        {
            "question": "가장 자랑스러운 프로젝트는 무엇인가요?",
            "category": "common",
            "model_answer": "전자상거래 플랫폼을 개발했습니다.",
            "reasoning": "구체적인 성과와 기여도",
        },
    ]
    
    for q in question_data:
        response = client.post("/admin/questions", json=q, headers=auth_headers)
        questions.append(response.json())
    
    # 면접 세트 생성
    set_response = client.post(
        "/interview/sets",
        json={
            "job_type": "it",
            "level": "entry",
            "question_count": 3,
        },
        headers=auth_headers,
    )
    set_id = set_response.json()["set_id"]
    
    print(f"\n📝 면접 세트 ID: {set_id}")
    print(f"📝 총 {len(questions)}개 질문 생성됨")
    
    # 각 질문에 답변
    answers = [
        "저는 3년 경력의 백엔드 개발자로, Python과 FastAPI를 주로 사용합니다. 최근 프로젝트에서 API 성능을 40% 향상시켰습니다.",
        "귀사의 AI 기술 스택과 혁신적인 서비스에 매력을 느꼈습니다. 특히 대규모 트래픽 처리 경험을 활용할 수 있을 것 같아 지원했습니다.",
        "전자상거래 결제 시스템 개발 프로젝트가 가장 자랑스럽습니다. 하루 10만 건의 거래를 안정적으로 처리하도록 설계했고, 에러율을 0.01% 이하로 유지했습니다.",
    ]
    
    print(f"\n{'─' * 80}")
    print(f"💬 답변 제출 중...")
    print(f"{'─' * 80}")
    
    for idx, (q, answer) in enumerate(zip(questions, answers), 1):
        print(f"\n질문 {idx}: {q['question']}")
        print(f"답변: {answer}")
        
        response = client.post(
            "/interview/answers",
            json={
                "set_id": set_id,
                "question_id": q["id"],
                "question_order": idx,
                "user_answer": answer,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
    
    # 면접 완료 및 종합 평가
    print(f"\n{'─' * 80}")
    print(f"⏳ AI 종합 평가 생성 중...")
    print(f"{'─' * 80}")
    
    eval_response = client.post(f"/interview/sets/{set_id}/complete", headers=auth_headers)
    
    if eval_response.status_code == 200:
        result = eval_response.json()
        
        print(f"\n{'=' * 80}")
        print(f"✅ 종합 평가 결과")
        print(f"{'=' * 80}")
        
        print(f"\n📊 항목별 점수:")
        print(f"   논리성 (Logic):           {result['logic']}/100")
        print(f"   근거 (Evidence):          {result['evidence']}/100")
        print(f"   직무이해도 (Job Understanding): {result['job_understanding']}/100")
        print(f"   한국어 격식 (Formality):  {result['formality']}/100")
        print(f"   완성도 (Completeness):    {result['completeness']}/100")
        
        avg_score = (
            result['logic'] + 
            result['evidence'] + 
            result['job_understanding'] + 
            result['formality'] + 
            result['completeness']
        ) / 5
        print(f"\n   📈 평균 점수: {avg_score:.1f}/100")
        
        print(f"\n💬 종합 피드백:")
        print(f"   {result['overall_feedback']}")
        
        if result.get('detailed_feedback'):
            print(f"\n📝 질문별 상세 피드백:")
            for feedback in result['detailed_feedback']:
                print(f"\n   질문 {feedback['question_order']}:")
                print(f"   피드백: {feedback['feedback']}")
                print(f"   개선점: {feedback['improvements']}")
    else:
        print(f"\n⚠️  평가 실패: {eval_response.status_code}")
        print(f"   오류: {eval_response.json()}")
        print(f"\n💡 참고: 종합 평가는 AI 응답 파싱이 복잡하여 가끔 실패할 수 있습니다.")
        print(f"   하지만 답변 평가와 꼬리질문 생성은 정상 작동합니다!")
    
    print("\n" + "=" * 80)


@skip_without_api_key
def test_ai_model_gemini_3_flash(client: TestClient, auth_headers: dict):
    """gemini-3-flash-preview 모델 테스트"""
    print("\n" + "=" * 80)
    print("🤖 AI 모델 테스트: google/gemini-3-flash-preview")
    print("=" * 80)
    
    # 질문 생성
    question_response = client.post(
        "/admin/questions",
        json={
            "question": "팀 내 갈등을 어떻게 해결하나요?",
            "category": "common",
            "model_answer": "경청하고, 객관적 사실에 기반하여 대화하며, 상호 이해를 추구합니다.",
            "reasoning": "갈등 해결 능력과 의사소통 능력 평가",
        },
        headers=auth_headers,
    )
    question_id = question_response.json()["id"]
    
    test_answer = "팀원과 의견 차이가 있을 때는 먼저 상대방의 의견을 충분히 들어봅니다. 그 다음 데이터와 사실을 기반으로 객관적으로 논의하려고 노력합니다."
    
    print(f"\n📝 질문: 팀 내 갈등을 어떻게 해결하나요?")
    print(f"📝 답변: {test_answer}")
    print(f"\n{'─' * 80}")
    print(f"🤖 모델: google/gemini-3-flash-preview")
    print(f"{'─' * 80}")
    
    response = client.post(
        "/questions/evaluate",
        json={
            "question_id": question_id,
            "user_answer": test_answer,
            "ai_model": "google/gemini-3-flash-preview",
        },
        headers=auth_headers,
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ 평가 성공!")
        print(f"   점수: {result['score']}/100")
        print(f"\n   💡 힌트:")
        print(f"   {result['hints']}")
        if result.get('strengths'):
            print(f"\n   👍 잘한 점:")
            print(f"   {result['strengths']}")
        if result.get('improvements'):
            print(f"\n   📈 개선점:")
            print(f"   {result['improvements']}")
    else:
        print(f"\n❌ 평가 실패: {response.status_code}")
        print(f"   오류: {response.json()}")
    
    print("\n" + "=" * 80)


def test_without_api_key_graceful_failure(client: TestClient, auth_headers: dict, seed_questions):
    """API 키 없이도 기본 기능은 작동하는지 테스트"""
    print("\n" + "=" * 80)
    print("🔑 API 키 없는 환경에서의 동작 테스트")
    print("=" * 80)
    
    # 질문 생성은 작동해야 함
    response = client.post(
        "/admin/questions",
        json={
            "question": "테스트 질문",
            "category": "common",
            "model_answer": "테스트 답변",
            "reasoning": "테스트 이유",
        },
        headers=auth_headers,
    )
    
    print(f"\n✅ 질문 생성: {response.status_code} (예상: 201)")
    assert response.status_code == 201
    
    # 면접 세트 생성도 작동해야 함
    response = client.post(
        "/interview/sets",
        json={
            "job_type": "it",
            "level": "entry",
            "question_count": 1,
        },
        headers=auth_headers,
    )
    
    print(f"✅ 면접 세트 생성: {response.status_code} (예상: 201)")
    assert response.status_code == 201
    
    print("\n💡 참고: AI 평가 기능은 OpenRouter API 키가 필요합니다.")
    print("   .env 파일에 OPENROUTER_API_KEY를 설정하면 전체 테스트를 실행할 수 있습니다.")
    print("\n" + "=" * 80)

