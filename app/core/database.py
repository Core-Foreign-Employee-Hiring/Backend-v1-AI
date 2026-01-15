from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import settings

# SQLite 연결 설정
connect_args = {"check_same_thread": False}
engine = create_engine(settings.database_url, connect_args=connect_args, echo=False)


def create_db_and_tables():
    """데이터베이스 테이블 생성"""
    SQLModel.metadata.create_all(engine)


def seed_initial_questions():
    """초기 테스트 질문 데이터 시딩 (설정으로 ON/OFF 가능)"""
    if not settings.seed_initial_questions:
        print("[INFO] 초기 질문 시딩 비활성화됨 (SEED_INITIAL_QUESTIONS=False)")
        return

    from app.models import Question

    with Session(engine) as session:
        # 이미 질문이 있으면 시딩하지 않음
        existing_count = len(session.exec(select(Question)).all())
        if existing_count > 0:
            print(f"[INFO] 이미 {existing_count}개의 질문이 존재합니다. 시딩을 건너뜁니다.")
            return

        print("[INFO] 초기 테스트 질문 시딩 시작...")

        # 공통 질문 4개
        common_questions = [
            Question(
                question="자기소개를 해주세요.",
                category="common",
                model_answer="안녕하세요. 저는 [이름]입니다. [출신 국가]에서 왔으며, [전공/배경]을 전공했습니다. 한국에서 [직무]로 일하고 싶어 지원하게 되었습니다. 저의 강점은 [강점]이며, 귀사에서 [기여할 점]을 통해 성장하고 싶습니다.",
                reasoning="자기소개는 간결하면서도 핵심 정보(출신, 전공, 지원동기, 강점)를 포함해야 합니다. 한국어로 자연스럽게 말하는 것이 중요합니다.",
            ),
            Question(
                question="우리 회사에 지원한 이유는 무엇인가요?",
                category="common",
                model_answer="귀사는 [산업/분야]에서 선도적인 위치에 있으며, [회사의 특징/비전]에 깊이 공감했습니다. 특히 [구체적인 프로젝트/제품/문화]가 인상 깊었고, 제 경험과 역량을 활용하여 귀사의 성장에 기여하고 싶습니다.",
                reasoning="회사에 대한 사전 조사와 이해를 보여주고, 본인의 목표와 회사의 방향이 일치함을 구체적으로 설명해야 합니다.",
            ),
            Question(
                question="본인의 강점과 약점은 무엇인가요?",
                category="common",
                model_answer="제 강점은 [구체적 강점]입니다. 예를 들어 [사례]에서 이를 발휘했습니다. 약점은 [약점]이지만, 이를 개선하기 위해 [구체적 노력]을 하고 있습니다.",
                reasoning="강점은 구체적 사례와 함께 설명하고, 약점은 개선 노력을 함께 언급하여 성장 가능성을 보여줘야 합니다.",
            ),
            Question(
                question="10년 후 본인의 모습은 어떨 것 같나요?",
                category="common",
                model_answer="10년 후에는 [직무 분야]의 전문가로 성장하여, [구체적 목표]를 달성하고 싶습니다. 이를 위해 지속적으로 [학습/개발 계획]하며, 팀과 조직에 긍정적인 영향을 주는 사람이 되고 싶습니다.",
                reasoning="구체적이면서도 현실적인 비전을 제시하고, 회사에서의 장기 근속 의지를 보여줘야 합니다.",
            ),
        ]

        # IT 직무 질문 3개
        it_questions = [
            Question(
                question="가장 자신 있는 프로그래밍 언어는 무엇이며, 어떤 프로젝트에 사용했나요?",
                category="job",
                job_type="it",
                level="entry",
                model_answer="저는 [언어]에 가장 자신 있습니다. [프로젝트명]에서 [구체적 기능]을 구현했으며, [기술적 도전과 해결 방법]을 경험했습니다. 이를 통해 [배운 점]을 얻었습니다.",
                reasoning="단순히 언어 이름만 말하는 것이 아니라, 실제 프로젝트 경험과 문제 해결 과정을 구체적으로 설명해야 기술 역량을 입증할 수 있습니다.",
            ),
            Question(
                question="팀 프로젝트에서 기술적 의견 충돌이 있었을 때 어떻게 해결했나요?",
                category="job",
                job_type="it",
                level="entry",
                model_answer="[프로젝트]에서 [기술 선택/구조]에 대한 의견 차이가 있었습니다. 저는 각 방식의 장단점을 분석하여 팀원들과 공유했고, [근거]를 바탕으로 [결정]했습니다. 결과적으로 [성과]를 얻었습니다.",
                reasoning="기술적 소통 능력과 협업 능력을 보여주는 것이 중요합니다. 논리적 근거와 팀워크를 강조해야 합니다.",
            ),
            Question(
                question="최근에 학습한 새로운 기술이나 프레임워크가 있나요?",
                category="job",
                job_type="it",
                level="entry",
                model_answer="최근 [기술/프레임워크]를 학습했습니다. [학습 방법]을 통해 공부했으며, [토이 프로젝트/실습]에 적용해봤습니다. 이 기술은 [장점]이 있어 실무에서도 활용하고 싶습니다.",
                reasoning="지속적인 학습 의지와 기술 트렌드에 대한 관심을 보여줘야 합니다. 단순 이론이 아닌 실습 경험을 언급하는 것이 좋습니다.",
            ),
        ]

        # 외국인특화 질문 3개
        foreigner_questions = [
            Question(
                question="한국어를 어떻게 공부했으며, 현재 수준은 어느 정도인가요?",
                category="foreigner",
                model_answer="한국어는 [학습 방법]을 통해 공부했으며, 현재 [TOPIK 급수/수준]입니다. 업무상 필요한 비즈니스 한국어는 [경험/노력]을 통해 익혔고, 지속적으로 향상시키고 있습니다.",
                reasoning="한국어 능력과 함께 업무에 필요한 의사소통 능력을 강조하고, 지속적인 학습 의지를 보여줘야 합니다.",
            ),
            Question(
                question="한국 문화나 업무 환경에 적응하는 데 어려움은 없나요?",
                category="foreigner",
                model_answer="처음에는 [구체적 어려움]이 있었지만, [적응 노력]을 통해 극복했습니다. 한국의 [긍정적 특징]을 배우며 적응했고, 문화 차이를 존중하면서 유연하게 대응하는 법을 익혔습니다.",
                reasoning="어려움을 솔직히 인정하되, 이를 극복한 구체적 경험과 긍정적 태도를 보여주는 것이 중요합니다.",
            ),
            Question(
                question="한국에서 장기적으로 일할 계획이 있나요?",
                category="foreigner",
                model_answer="네, 한국에서 장기적으로 일하며 성장하고 싶습니다. [구체적 이유]로 인해 한국이 제 커리어에 적합하다고 생각하며, [비자/정착 계획]도 준비하고 있습니다. 귀사와 함께 장기적으로 성장하고 싶습니다.",
                reasoning="장기 근속 의지와 구체적인 계획을 보여줘야 회사가 안심하고 채용할 수 있습니다.",
            ),
        ]

        # 모든 질문 추가
        all_questions = common_questions + it_questions + foreigner_questions

        for question in all_questions:
            session.add(question)

        session.commit()

        print(f"[SUCCESS] {len(all_questions)}개의 초기 질문이 추가되었습니다.")
        print(f"  - 공통 질문: {len(common_questions)}개")
        print(f"  - IT 직무 질문: {len(it_questions)}개")
        print(f"  - 외국인특화 질문: {len(foreigner_questions)}개")


def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션 의존성"""
    with Session(engine) as session:
        yield session
