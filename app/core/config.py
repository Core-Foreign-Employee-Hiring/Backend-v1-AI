from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # 정의되지 않은 환경변수 무시
    )

    database_url: str = "sqlite:///./database.db"
    secret_key: str = "your-secret-key-change-this-in-production"

    # OpenRouter API 설정
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    default_ai_model: str = "google/gemini-3-flash-preview"

    # 선택적 헤더 (OpenRouter 리더보드용)
    app_url: str = ""
    app_name: str = "면접 AI 서비스"

    # 초기 데이터 시딩 (ON/OFF 가능)
    seed_initial_questions: bool = True


settings = Settings()