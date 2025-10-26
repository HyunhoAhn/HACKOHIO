from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from app.controller.conversation_controller import router as conversation_router
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 시작/종료 시 실행되는 lifespan 이벤트
    """
    # Startup
    print("🚀 Starting up Hawk English Learning API...")
    print("📦 Loading AI models...")
    
    # Whisper 모델 로드 (명시적으로 로드하여 reloader 문제를 피함)
    from app.service.whisper_service import whisper_service
    # Load model once during application startup (lazy-load otherwise)
    whisper_service.load_model()
    print("✅ Whisper model loaded (initialized)")
    
    print("✅ All models loaded successfully!")
    print("🎉 API is ready to serve requests")
    
    yield
    
    # Shutdown
    print("👋 Shutting down Hawk English Learning API...")


app = FastAPI(
    title="Hawk English Learning API",
    description="AI-powered English conversation practice with pronunciation feedback",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 (오디오 파일)
audio_storage_path = Path(settings.AUDIO_STORAGE_PATH)
audio_storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_storage_path)), name="audio")

# 라우터 등록
app.include_router(conversation_router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Hawk English Learning API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "Hawk English Learning API"
    }
