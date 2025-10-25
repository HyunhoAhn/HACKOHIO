from functools import lru_cache
from dotenv import load_dotenv
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SPEECH_KEY: str
    SPEECH_REGION: str
    ENV: str = "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    load_dotenv()
    return Settings()


if __name__ == "__main__":
    settings = get_settings()
    print(settings.SPEECH_KEY, settings.SPEECH_REGION)
