import whisper
import numpy as np
import wave
from pathlib import Path
from app.config import get_settings

settings = get_settings()


class WhisperService:
    def __init__(self):
        # Defer heavy model loading until explicitly requested to avoid
        # loading the model at module import time (which causes double-load
        # when uvicorn's reloader spawns watcher and worker processes).
        self.model = None
        self.model_size = settings.WHISPER_MODEL_SIZE

    def load_model(self):
        """Load the Whisper model if it isn't already loaded."""
        if self.model is None:
            print(f"Loading Whisper {self.model_size} model...")
            self.model = whisper.load_model(self.model_size)
            print("Whisper model loaded!")
    
    def transcribe(self, audio_file_path: str) -> str:
        """
        Whisper를 사용하여 음성을 텍스트로 변환
        
        Args:
            audio_file_path: WAV 파일 경로
            
        Returns:
            str: 인식된 텍스트
        """
        # ensure model is loaded (lazy)
        if self.model is None:
            self.load_model()

        result = self.model.transcribe(
            str(audio_file_path),
            language="en",
            fp16=False,
            verbose=False
        )
        return result["text"].strip()
    
    def split_into_sentences(self, text: str) -> list[str]:
        """
        텍스트를 문장 단위로 분할
        간단한 구현: ., !, ? 기준으로 분할
        
        Args:
            text: 전체 텍스트
            
        Returns:
            List[str]: 문장 리스트
        """
        import re
        # 문장 종결 부호로 분할
        sentences = re.split(r'[.!?]+', text)
        # 빈 문장 제거 및 공백 정리
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences


# 싱글톤 인스턴스
whisper_service = WhisperService()
