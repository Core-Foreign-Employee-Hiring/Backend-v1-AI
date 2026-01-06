import base64
import json
import re

from openai import OpenAI

from app.core.config import settings

def create_openrouter_client() -> OpenAI:
    """OpenRouter 클라이언트 생성"""
    return OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
    )


def strip_markdown_code_fences(text: str) -> str:
    """마크다운 코드 블록 제거 (```json``` 등)"""
    # ```json\n{...}\n``` 형태 제거
    text = re.sub(r"```(?:json)?\s*\n?", "", text)
    text = text.strip()
    return text


async def transcribe_audio_base64(
    audio_base64: str,
    audio_format: str,
    model: str | None = None,
) -> str:
    """
    Base64 인코딩된 오디오를 텍스트로 변환
    
    OpenRouter는 Whisper API를 직접 지원하지 않으므로,
    실제로는 OpenAI Whisper API를 별도로 호출해야 합니다.
    """
    # TODO: OpenAI Whisper API 또는 다른 음성 전사 서비스 구현
    # 현재는 더미 구현
    raise NotImplementedError("음성 전사 기능은 아직 구현되지 않았습니다")


def evaluate_answer_with_ai(
    question: str,
    model_answer: str,
    reasoning: str,
    user_answer: str,
    ai_model: str | None = None,
) -> dict:
    """AI로 사용자 답변 평가"""
    client = create_openrouter_client()
    model = ai_model or settings.default_ai_model

    system_prompt = f"""당신은 면접관입니다. 지원자의 답변을 평가하고 개선점을 제시합니다.

면접 질문: {question}
모범답안: {model_answer}
모범답안의 논리와 이유: {reasoning}

지원자의 답변을 평가하여:
1. 모범답안과의 유사도를 0-100점으로 점수화하세요
2. 지원자가 더 나은 답변을 할 수 있도록 구체적인 힌트를 제공하세요
3. 답변에서 잘한 점과 개선이 필요한 점을 명확히 지적하세요

응답은 반드시 다음 JSON 형식으로 제공하세요:
{{
  "score": <0-100 사이의 숫자>,
  "hints": "<구체적인 힌트와 피드백>",
  "strengths": "<잘한 점>",
  "improvements": "<개선이 필요한 점>"
}}"""

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"지원자의 답변: {user_answer}"},
            ],
            max_tokens=3000,
            temperature=0.7,
        )

        ai_response = completion.choices[0].message.content or "{}"
        
        # 디버깅: 원본 응답 로그
        print(f"[DEBUG] AI 답변 평가 원본 응답 (첫 500자): {ai_response[:500]}")
        
        cleaned = strip_markdown_code_fences(ai_response)
        
        # 디버깅: 정제된 응답 로그
        print(f"[DEBUG] AI 답변 평가 정제된 응답 (첫 500자): {cleaned[:500]}")
        
        if not cleaned.strip():
            raise ValueError("AI 응답이 비어있습니다")
        
        evaluation = json.loads(cleaned)

        return {
            "score": evaluation.get("score", 0),
            "hints": evaluation.get("hints", ""),
            "strengths": evaluation.get("strengths", ""),
            "improvements": evaluation.get("improvements", ""),
            "raw_response": ai_response,
        }
    except json.JSONDecodeError as e:
        print(f"[ERROR] AI 답변 평가 JSON 파싱 실패: {str(e)}")
        print(f"[ERROR] 파싱 실패한 내용: {cleaned}")
        raise Exception(f"AI 답변 평가 JSON 파싱 실패: {str(e)}")
    except Exception as e:
        print(f"[ERROR] AI 답변 평가 중 에러: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise Exception(f"AI 평가 실패: {str(e)}")


def generate_follow_up_question(
    question: str | None,
    user_answer: str,
    ai_model: str | None = None,
) -> str:
    """AI로 꼬리질문 생성"""
    client = create_openrouter_client()
    model = ai_model or settings.default_ai_model

    prompt = f"""당신은 한국 기업의 면접관입니다. 지원자의 답변을 듣고 압박 꼬리질문을 생성하세요.

{"원래 질문: " + question if question else ""}
지원자 답변: {user_answer}

지원자의 답변에서 핵심 키워드를 파악하고, 그 내용을 더 깊이 파고들거나 구체적인 근거를 요구하는 압박 꼬리질문 1개를 생성하세요.
질문은 자연스럽고 실전 면접처럼 만들어주세요.

JSON 형식으로 응답:
{{
  "followUpQuestion": "<꼬리질문>"
}}"""

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=1000,
        )

        response = completion.choices[0].message.content or "{}"
        
        # 디버깅: 꼬리질문 응답 로그
        print(f"[DEBUG] 꼬리질문 생성 원본 응답 (첫 300자): {response[:300]}")
        
        cleaned = strip_markdown_code_fences(response)
        
        print(f"[DEBUG] 꼬리질문 생성 정제된 응답 (첫 300자): {cleaned[:300]}")
        
        if not cleaned.strip():
            raise ValueError("AI 응답이 비어있습니다")
        
        parsed = json.loads(cleaned)
        return parsed.get("followUpQuestion", "")
    except json.JSONDecodeError as e:
        print(f"[ERROR] 꼬리질문 JSON 파싱 실패: {str(e)}")
        print(f"[ERROR] 파싱 실패한 내용: {cleaned}")
        raise Exception(f"꼬리질문 JSON 파싱 실패: {str(e)}")
    except Exception as e:
        print(f"[ERROR] 꼬리질문 생성 중 에러: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise Exception(f"꼬리질문 생성 실패: {str(e)}")


def evaluate_interview_comprehensive(
    answers_data: list[dict],
) -> dict:
    """면접 종합 평가"""
    client = create_openrouter_client()
    model = settings.default_ai_model

    # 답변 정리
    answers_text = "\n".join(
        [
            f"""
질문 {i + 1}: {a['question']}
답변: {a['user_answer']}
{f"꼬리질문: {a['follow_up_question']}" if a.get('follow_up_question') else ''}
{f"꼬리답변: {a.get('follow_up_answer', '(답변 없음)')}" if a.get('follow_up_question') else ''}
"""
            for i, a in enumerate(answers_data)
        ]
    )

    num_questions = len(answers_data)
    evaluation_prompt = f"""당신은 한국 기업의 인사담당자입니다. 외국인 지원자의 면접 답변을 종합 평가하세요.

면접 답변:
{answers_text}

다음 5가지 항목을 0-100점으로 평가하고, 종합 피드백을 제공하세요:
1. logic (논리성): 답변의 논리적 구조와 일관성
2. evidence (근거): 구체적인 사례와 근거 제시
3. jobUnderstanding (직무이해도): 지원 직무에 대한 이해도
4. formality (한국어 격식): 비즈니스 한국어 사용 적절성
5. completeness (완성도): 답변의 완성도와 충실성

⚠️ 중요: 질문은 총 {num_questions}개입니다. detailedFeedback 배열도 정확히 {num_questions}개의 항목만 포함해야 합니다.

JSON 형식으로 응답 (반드시 이 형식을 따르세요):
{{
  "logic": <점수>,
  "evidence": <점수>,
  "jobUnderstanding": <점수>,
  "formality": <점수>,
  "completeness": <점수>,
  "overallFeedback": "<전체 종합 피드백>",
  "detailedFeedback": [
    {{
      "questionOrder": 1,
      "feedback": "<질문 1에 대한 상세 피드백>",
      "improvements": "<개선 제안>"
    }}
    {"," if num_questions > 1 else ""}
    {"..." if num_questions > 1 else ""}
  ]
}}"""

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": evaluation_prompt}],
            temperature=0.7,
            max_tokens=5000,
        )

        response = completion.choices[0].message.content or "{}"
        cleaned = strip_markdown_code_fences(response)
        
        if not cleaned.strip():
            raise ValueError("AI 응답이 비어있습니다")
        
        # JSON 유효성 검사
        try:
            evaluation = json.loads(cleaned)
        except json.JSONDecodeError as e:
            # JSON 파싱 실패 시 전체 응답 출력
            print(f"[ERROR] JSON 파싱 실패! 전체 응답:")
            print(cleaned)
            raise

        # AI 응답의 detailedFeedback에 실제 질문/답변 데이터 추가
        detailed_feedback = evaluation.get("detailedFeedback", [])
        enriched_feedback = []
        
        for item in detailed_feedback:
            question_order = item.get("questionOrder", 0)
            # questionOrder는 1부터 시작, 배열 인덱스는 0부터
            if 1 <= question_order <= len(answers_data):
                answer_data = answers_data[question_order - 1]
                enriched_item = {
                    "questionOrder": question_order,
                    "question": answer_data.get("question", ""),
                    "userAnswer": answer_data.get("user_answer", ""),
                    "followUpQuestion": answer_data.get("follow_up_question"),
                    "followUpAnswer": answer_data.get("follow_up_answer"),
                    "feedback": item.get("feedback", ""),
                    "improvements": item.get("improvements", ""),
                }
                enriched_feedback.append(enriched_item)
            else:
                # questionOrder가 범위를 벗어나면 원본 그대로 추가
                enriched_feedback.append(item)
        
        return {
            "logic": evaluation.get("logic", 0),
            "evidence": evaluation.get("evidence", 0),
            "jobUnderstanding": evaluation.get("jobUnderstanding", 0),
            "formality": evaluation.get("formality", 0),
            "completeness": evaluation.get("completeness", 0),
            "overallFeedback": evaluation.get("overallFeedback", ""),
            "detailedFeedback": enriched_feedback,
        }
    except json.JSONDecodeError as e:
        print(f"[ERROR] 종합 평가 JSON 파싱 실패: {str(e)}")
        print(f"[ERROR] 파싱 실패한 내용: {cleaned}")
        raise Exception(f"종합 평가 JSON 파싱 실패: {str(e)}")
    except Exception as e:
        print(f"[ERROR] 종합 평가 중 에러: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise Exception(f"종합 평가 실패: {str(e)}")

