import azure.cognitiveservices.speech as speechsdk
from pathlib import Path
from app.config import get_settings

settings = get_settings()


class PollyService:
    """Azure Speech Service를 사용한 TTS (Polly 대체)"""
    
    def __init__(self):
        try:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=settings.AZURE_SPEECH_KEY,
                region=settings.AZURE_REGION
            )
            # 영어 음성 설정
            self.speech_config.speech_synthesis_voice_name = "en-US-AndrewMultilingualNeural"
            self.available = True
        except Exception as e:
            print(f"⚠️ Azure Speech TTS initialization error: {e}")
            self.available = False
        
    def text_to_speech(self, text: str, output_path: str) -> str:
        """
        텍스트를 음성으로 변환 (Azure Speech Service)
        
        Args:
            text: 변환할 텍스트
            output_path: 저장할 파일 경로
            
        Returns:
            str: 저장된 파일 경로
        """
        if not self.available:
            print(f"⚠️ Azure Speech TTS not available")
            return self._create_dummy_file(output_path)
        
        try:
            # 파일 경로 준비
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # MP3 대신 WAV로 저장 (Azure는 WAV를 기본 지원)
            if output_file.suffix == '.mp3':
                output_file = output_file.with_suffix('.wav')
            
            # 오디오 출력 설정
            audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_file))
            
            # 음성 합성기 생성
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # 음성 합성 실행
            result = synthesizer.speak_text_async(text).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print(f"✅ Azure TTS generated: {output_file.name}")
                return str(output_file)
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                print(f"⚠️ Azure TTS canceled: {cancellation.reason}")
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    print(f"⚠️ Error details: {cancellation.error_details}")
                return self._create_dummy_file(output_path)
            else:
                print(f"⚠️ Azure TTS unexpected result: {result.reason}")
                return self._create_dummy_file(output_path)
            
        except Exception as e:
            print(f"⚠️ Azure TTS error: {e}")
            return self._create_dummy_file(output_path)
    
    def _create_dummy_file(self, output_path: str) -> str:
        """더미 오디오 파일 생성"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 빈 WAV 파일 생성 (최소한의 유효한 WAV 헤더)
        dummy_wav = bytes([
            0x52, 0x49, 0x46, 0x46,  # "RIFF"
            0x24, 0x00, 0x00, 0x00,  # ChunkSize
            0x57, 0x41, 0x56, 0x45,  # "WAVE"
            0x66, 0x6D, 0x74, 0x20,  # "fmt "
            0x10, 0x00, 0x00, 0x00,  # Subchunk1Size
            0x01, 0x00, 0x01, 0x00,  # AudioFormat, NumChannels
            0x44, 0xAC, 0x00, 0x00,  # SampleRate
            0x88, 0x58, 0x01, 0x00,  # ByteRate
            0x02, 0x00, 0x10, 0x00,  # BlockAlign, BitsPerSample
            0x64, 0x61, 0x74, 0x61,  # "data"
            0x00, 0x00, 0x00, 0x00   # Subchunk2Size
        ])
        
        with open(output_file, "wb") as f:
            f.write(dummy_wav)
        
        print(f"⚠️ Created dummy audio file (Azure TTS not available)")
        return str(output_file)


# 싱글톤 인스턴스
polly_service = PollyService()
