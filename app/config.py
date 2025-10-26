from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = ""
    
    # Azure Speech
    AZURE_SPEECH_KEY: str = ""
    AZURE_REGION: str = ""
    
    # Google Gemini
    GEMINI_API_KEY: str = ""  # 환경변수에서 가져오기
    
    # Whisper
    WHISPER_MODEL_SIZE: str = "large-v3"
    
    # Audio settings
    SAMPLE_RATE: int = 16000
    
    # File storage
    AUDIO_STORAGE_PATH: str = "./audio_files"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
