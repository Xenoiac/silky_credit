import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    env: str
    db_url: str
    openai_api_key: str
    openai_model: str
    log_level: str
    project_name: str = "Silky Credit & Behaviour Engine"

    @property
    def is_dev(self) -> bool:
        return self.env.lower() == "dev"


def load_settings() -> Settings:
    env = os.getenv("ENV", "dev")
    db_url = os.getenv("DB_URL", "sqlite:///./silky_credit.db")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    openai_model = os.getenv("OPENAI_MODEL", "gpt-5.1")
    log_level = os.getenv("LOG_LEVEL", "INFO")

    return Settings(
        env=env,
        db_url=db_url,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        log_level=log_level,
    )


settings = load_settings()
