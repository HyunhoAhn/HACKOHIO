import azure.cognitiveservices.speech as speechsdk
from uuid import UUID
from app.config import get_settings
from app.models import AzurePronunciationResult, WordError

settings = get_settings()


class AzureSpeechService:
    def __init__(self):
        self.speech_key = settings.AZURE_SPEECH_KEY
        self.region = settings.AZURE_REGION
        
    def assess_pronunciation(
        self, 
        audio_file_path: str, 
        reference_text: str,
        sentence_id: UUID,
        sentence_number: int
    ) -> AzurePronunciationResult:
        """
        Azure Speech를 사용하여 발음 평가
        
        Args:
            audio_file_path: WAV 파일 경로
            reference_text: 참조 텍스트 (정답)
            sentence_id: 문장 ID
            sentence_number: 문장 번호
            
        Returns:
            AzurePronunciationResult: 발음 평가 결과
        """
        try:
            # Azure Speech Config 설정
            speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.region
            )
            
            # 오디오 파일에서 입력
            audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)
            
            # 발음 평가 설정
            pronunciation_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=True
            )
            
            # Speech Recognizer 생성
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            
            # 발음 평가 적용
            pronunciation_config.apply_to(recognizer)
            
            # 인식 실행
            result = recognizer.recognize_once()
            
            # 결과 처리
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                pronunciation_result = speechsdk.PronunciationAssessmentResult(result)
                
                # JSON 파싱
                import json
                json_result = json.loads(result.properties.get(
                    speechsdk.PropertyId.SpeechServiceResponse_JsonResult
                ))
                
                # 단어별 결과 파싱
                words_data = []
                errors = []
                
                if "NBest" in json_result and len(json_result["NBest"]) > 0:
                    words = json_result["NBest"][0].get("Words", [])
                    
                    for word_data in words:
                        words_data.append(word_data)
                        
                        # 에러 판정 (정확도가 낮은 경우)
                        accuracy = word_data.get("PronunciationAssessment", {}).get("AccuracyScore", 100)
                        error_type = word_data.get("PronunciationAssessment", {}).get("ErrorType", "None")
                        
                        if accuracy < 60 or error_type != "None":
                            error = WordError(
                                word=word_data.get("Word", ""),
                                phoneme=None,  # 추후 상세 분석 가능
                                error_type=error_type,
                                accuracy_score=accuracy,
                                expected_phoneme=None,
                                actual_phoneme=None
                            )
                            errors.append(error)
                
                return AzurePronunciationResult(
                    sentence_id=sentence_id,
                    sentence_number=sentence_number,
                    text=reference_text,
                    recognized_text=result.text,
                    pronunciation_score=pronunciation_result.pronunciation_score,
                    accuracy_score=pronunciation_result.accuracy_score,
                    fluency_score=pronunciation_result.fluency_score,
                    completeness_score=pronunciation_result.completeness_score,
                    prosody_score=getattr(pronunciation_result, 'prosody_score', None),
                    words=words_data,
                    errors=errors,
                    azure_raw_data=json_result
                )
            else:
                # 인식 실패
                raise Exception(f"Azure recognition failed: {result.reason}")
                
        except Exception as e:
            print(f"Azure pronunciation assessment error: {e}")
            # 에러 시 기본값 반환
            return AzurePronunciationResult(
                sentence_id=sentence_id,
                sentence_number=sentence_number,
                text=reference_text,
                recognized_text="",
                pronunciation_score=0.0,
                accuracy_score=0.0,
                fluency_score=0.0,
                completeness_score=0.0,
                prosody_score=None,
                words=[],
                errors=[],
                azure_raw_data={"error": str(e)}
            )


# 싱글톤 인스턴스
azure_speech_service = AzureSpeechService()
