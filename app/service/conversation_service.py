from uuid import UUID, uuid4
from datetime import datetime
from pathlib import Path
from typing import List
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import wave
import subprocess

from app.database import db
from app.models import (
    StartConversationResponse,
    GenerateTranscriptionResponse,
    EndConversationResponse,
    TurnFeedback,
    SentenceScore,
    WordError,
    AzurePronunciationResult,
    GeminiFeedbackResult
)
from app.service.whisper_service import whisper_service
from app.service.azure_service import azure_speech_service
from app.service.gemini_service import gemini_service
from app.service.polly_service import polly_service
from app.config import get_settings

settings = get_settings()


class ConversationService:
    """대화 관련 비즈니스 로직"""
    
    def __init__(self):
        self.audio_storage = Path(settings.AUDIO_STORAGE_PATH)
        self.audio_storage.mkdir(parents=True, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    def start_conversation(self, user_id: UUID, topic: str = None) -> StartConversationResponse:
        """
        새로운 대화 세션 시작
        
        Args:
            user_id: 사용자 ID
            topic: 대화 주제 (optional)
            
        Returns:
            StartConversationResponse
        """
        conversation_id = uuid4()
        started_at = datetime.now()
        
        # DB에 대화 생성
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO conversations (conversation_id, user_id, topic, started_at, status)
                VALUES (%s, %s, %s, %s, 'active')
                """,
                (conversation_id, user_id, topic, started_at)
            )
        
        # 환영 메시지 생성
        welcome_text = gemini_service.generate_welcome_message(topic)
        
        # TTS로 음성 생성 (Azure Speech는 WAV 형식)
        welcome_audio_filename = f"{conversation_id}_welcome.wav"
        welcome_audio_path = self.audio_storage / welcome_audio_filename
        polly_service.text_to_speech(welcome_text, str(welcome_audio_path))
        
        # HTTP URL로 반환
        welcome_audio_url = f"http://127.0.0.1:8000/audio/{welcome_audio_filename}"
        
        return StartConversationResponse(
            conversation_id=conversation_id,
            welcome_message_text=welcome_text,
            welcome_message_audio_url=welcome_audio_url,
            started_at=started_at
        )
    
    async def process_turn(
        self,
        conversation_id: UUID,
        turn_number: int,
        audio_file_path: str
    ) -> GenerateTranscriptionResponse:
        """
        턴 처리: STT → 발음평가 → 피드백 생성 → 대화 응답 생성
        
        Args:
            conversation_id: 대화 ID
            turn_number: 턴 번호
            audio_file_path: 사용자 음성 파일 경로
            
        Returns:
            GenerateTranscriptionResponse
        """
        turn_id = uuid4()
        created_at = datetime.now()
        
        # Step 0: 오디오 파일을 Azure 호환 형식으로 변환
        print(f"[Turn {turn_number}] Step 0: Converting audio to Azure format...")
        converted_audio_path = await self._convert_audio_for_azure(audio_file_path)
        
        # Step 1: Whisper로 STT
        print(f"[Turn {turn_number}] Step 1: Whisper STT...")
        user_text = await asyncio.to_thread(whisper_service.transcribe, audio_file_path)
        print(f"[Turn {turn_number}] Recognized: {user_text}")
        
        # Step 2: 문장 단위로 청크
        sentences = whisper_service.split_into_sentences(user_text)
        print(f"[Turn {turn_number}] Step 2: Split into {len(sentences)} sentences")
        
        # Step 3: 문장별로 병렬 Azure 발음 평가 (변환된 파일 사용)
        print(f"[Turn {turn_number}] Step 3: Azure pronunciation assessment...")
        azure_results = await self._parallel_azure_assessment(
            converted_audio_path,
            sentences,
            turn_id
        )
        
        # Step 4: DB에 턴 저장
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO turns (turn_id, conversation_id, turn_number, user_audio_url, user_text, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (turn_id, conversation_id, turn_number, audio_file_path, user_text, created_at)
            )
        
        # Step 5: DB에 문장별 저장
        for azure_result in azure_results:
            with db.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO sentences (
                        sentence_id, turn_id, sentence_number, text,
                        accuracy_score, fluency_score, completeness_score, prosody_score,
                        azure_raw_data, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        azure_result.sentence_id,
                        turn_id,
                        azure_result.sentence_number,
                        azure_result.text,
                        azure_result.accuracy_score,
                        azure_result.fluency_score,
                        azure_result.completeness_score,
                        azure_result.prosody_score,
                        json.dumps(azure_result.azure_raw_data),
                        created_at
                    )
                )
        
        # Step 6: 발음 오류 저장
        user_id = self._get_user_id_from_conversation(conversation_id)
        for azure_result in azure_results:
            for error in azure_result.errors:
                with db.get_cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO pronunciation_errors (
                            sentence_id, turn_id, user_id, word, phoneme, error_type,
                            accuracy_score, expected_phoneme, actual_phoneme, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            azure_result.sentence_id,
                            turn_id,
                            user_id,
                            error.word,
                            error.phoneme,
                            error.error_type,
                            error.accuracy_score,
                            error.expected_phoneme,
                            error.actual_phoneme,
                            created_at
                        )
                    )
        
        # Step 7: Gemini로 종합 피드백 생성
        print(f"[Turn {turn_number}] Step 4: Gemini comprehensive feedback...")
        gemini_feedback = await asyncio.to_thread(
            gemini_service.generate_comprehensive_feedback,
            user_text,
            azure_results
        )
        
        # Step 8: DB에 피드백 저장
        feedback_id = uuid4()
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO turn_feedback (
                    feedback_id, turn_id,
                    pronunciation_score, vocabulary_score, grammar_score, fluency_score, overall_score,
                    overall_comment, strengths, improvements, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    feedback_id,
                    turn_id,
                    gemini_feedback.pronunciation_score,
                    gemini_feedback.vocabulary_score,
                    gemini_feedback.grammar_score,
                    gemini_feedback.fluency_score,
                    gemini_feedback.overall_score,
                    gemini_feedback.overall_comment,
                    json.dumps(gemini_feedback.strengths),
                    json.dumps(gemini_feedback.improvements),
                    created_at
                )
            )
        
        # Step 9: 어휘/문법 오류 저장
        for vocab_error in gemini_feedback.vocabulary_errors:
            with db.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO vocabulary_errors (
                        turn_id, user_id, error_type, incorrect_phrase, correct_phrase, context, explanation, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        turn_id,
                        user_id,
                        "word_choice",
                        vocab_error.get("incorrect_phrase", ""),
                        vocab_error.get("correct_phrase", ""),
                        user_text,
                        vocab_error.get("explanation", ""),
                        created_at
                    )
                )
        
        for grammar_error in gemini_feedback.grammar_errors:
            with db.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO grammar_errors (
                        turn_id, user_id, error_type, incorrect_text, correct_text, rule_violated, explanation, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        turn_id,
                        user_id,
                        grammar_error.get("rule_violated", "unknown"),
                        grammar_error.get("incorrect_text", ""),
                        grammar_error.get("correct_text", ""),
                        grammar_error.get("rule_violated", ""),
                        grammar_error.get("explanation", ""),
                        created_at
                    )
                )
        
        # Step 10: 피드백 텍스트 생성 (TTS용)
        feedback_text = self._generate_feedback_text(gemini_feedback)
        feedback_audio_filename = f"{turn_id}_feedback.wav"
        feedback_audio_path = self.audio_storage / feedback_audio_filename
        await asyncio.to_thread(polly_service.text_to_speech, feedback_text, str(feedback_audio_path))
        
        # Step 11: 대화 응답 생성
        print(f"[Turn {turn_number}] Step 5: Generating conversation response...")
        conversation_history = self._get_conversation_history(conversation_id)
        llm_response_text = await asyncio.to_thread(
            gemini_service.generate_conversation_response,
            user_text,
            conversation_history
        )
        
        # LLM 응답 음성 생성
        llm_audio_filename = f"{turn_id}_response.wav"
        llm_audio_path = self.audio_storage / llm_audio_filename
        await asyncio.to_thread(polly_service.text_to_speech, llm_response_text, str(llm_audio_path))
        
        # DB에 LLM 응답 업데이트
        with db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE turns SET llm_response = %s WHERE turn_id = %s",
                (llm_response_text, turn_id)
            )
        
        # 대화 턴 수 업데이트
        with db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE conversations SET total_turns = total_turns + 1 WHERE conversation_id = %s",
                (conversation_id,)
            )
        
        print(f"[Turn {turn_number}] ✅ Complete!")
        
        # HTTP URL로 변환
        feedback_audio_url = f"http://127.0.0.1:8000/audio/{feedback_audio_filename}"
        llm_audio_url = f"http://127.0.0.1:8000/audio/{llm_audio_filename}"
        
        # 응답 구성
        return GenerateTranscriptionResponse(
            turn_id=turn_id,
            conversation_id=conversation_id,
            turn_number=turn_number,
            user_text=user_text,
            user_audio_url=audio_file_path,
            feedback=TurnFeedback(
                feedback_id=feedback_id,
                turn_id=turn_id,
                pronunciation_score=gemini_feedback.pronunciation_score,
                vocabulary_score=gemini_feedback.vocabulary_score,
                grammar_score=gemini_feedback.grammar_score,
                fluency_score=gemini_feedback.fluency_score,
                overall_score=gemini_feedback.overall_score,
                overall_comment=gemini_feedback.overall_comment,
                strengths=gemini_feedback.strengths,
                improvements=gemini_feedback.improvements,
                sentences=[
                    SentenceScore(
                        sentence_id=r.sentence_id,
                        sentence_number=r.sentence_number,
                        text=r.text,
                        accuracy_score=r.accuracy_score,
                        fluency_score=r.fluency_score,
                        completeness_score=r.completeness_score,
                        prosody_score=r.prosody_score
                    ) for r in azure_results
                ],
                pronunciation_errors=sum([r.errors for r in azure_results], []),
                vocabulary_errors=gemini_feedback.vocabulary_errors,
                grammar_errors=gemini_feedback.grammar_errors
            ),
            feedback_text=feedback_text,
            feedback_audio_url=feedback_audio_url,
            llm_response_text=llm_response_text,
            llm_response_audio_url=llm_audio_url,
            created_at=created_at
        )
    
    async def _convert_audio_for_azure(self, audio_file_path: str) -> str:
        """
        오디오 파일을 Azure Speech가 요구하는 형식으로 변환
        16kHz, 16-bit, mono, PCM WAV
        
        Args:
            audio_file_path: 원본 오디오 파일 경로
            
        Returns:
            str: 변환된 오디오 파일 경로
        """
        try:
            input_path = Path(audio_file_path)
            output_path = input_path.with_name(f"{input_path.stem}_azure.wav")
            
            # ffmpeg를 사용하여 변환
            cmd = [
                'ffmpeg',
                '-i', str(input_path),
                '-ar', '16000',  # 16kHz
                '-ac', '1',      # mono
                '-sample_fmt', 's16',  # 16-bit PCM
                '-y',  # 덮어쓰기
                str(output_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                print(f"⚠️ FFmpeg conversion failed: {stderr.decode()}")
                # 변환 실패 시 원본 파일 반환
                return audio_file_path
            
            print(f"✅ Audio converted for Azure: {output_path.name}")
            return str(output_path)
            
        except FileNotFoundError:
            print("⚠️ FFmpeg not found. Install with: brew install ffmpeg")
            return audio_file_path
        except Exception as e:
            print(f"⚠️ Audio conversion error: {e}")
            return audio_file_path
    
    async def _parallel_azure_assessment(
        self,
        audio_file_path: str,
        sentences: List[str],
        turn_id: UUID
    ) -> List[AzurePronunciationResult]:
        """
        문장들을 병렬로 Azure 발음 평가
        (실제로는 전체 오디오를 문장별로 나눠야 하지만, 여기서는 간소화)
        """
        tasks = []
        loop = asyncio.get_event_loop()
        
        for idx, sentence in enumerate(sentences):
            sentence_id = uuid4()
            # 실제로는 오디오를 문장별로 잘라야 함
            # 여기서는 전체 오디오로 각 문장 평가 (데모용)
            task = loop.run_in_executor(
                self.executor,
                azure_speech_service.assess_pronunciation,
                audio_file_path,
                sentence,
                sentence_id,
                idx + 1
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
    
    def _get_user_id_from_conversation(self, conversation_id: UUID) -> UUID:
        """대화 ID로부터 사용자 ID 조회"""
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM conversations WHERE conversation_id = %s",
                (conversation_id,)
            )
            result = cursor.fetchone()
            return result['user_id'] if result else None
    
    def _get_conversation_history(self, conversation_id: UUID) -> List[dict]:
        """대화 히스토리 조회"""
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT user_text, llm_response
                FROM turns
                WHERE conversation_id = %s
                ORDER BY turn_number
                LIMIT 10
                """,
                (conversation_id,)
            )
            rows = cursor.fetchall()
            
            history = []
            for row in rows:
                history.append({"role": "user", "content": row['user_text']})
                if row['llm_response']:
                    history.append({"role": "assistant", "content": row['llm_response']})
            
            return history
    
    def _generate_feedback_text(self, feedback: GeminiFeedbackResult) -> str:
        """피드백을 TTS용 텍스트로 변환"""
        text = f"Overall score: {feedback.overall_score:.0f} out of 100. "
        text += f"Pronunciation: {feedback.pronunciation_score:.0f}. "
        text += f"Grammar: {feedback.grammar_score:.0f}. "
        text += f"Vocabulary: {feedback.vocabulary_score:.0f}. "
        text += feedback.overall_comment
        return text
    
    def end_conversation(self, conversation_id: UUID) -> EndConversationResponse:
        """
        대화 종료
        
        Args:
            conversation_id: 대화 ID
            
        Returns:
            EndConversationResponse
        """
        ended_at = datetime.now()
        
        # 대화 상태 업데이트
        with db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE conversations SET status = 'completed', ended_at = %s WHERE conversation_id = %s",
                (ended_at, conversation_id)
            )
        
        # 통계 조회
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_turns,
                    AVG(tf.pronunciation_score) as avg_pronunciation,
                    AVG(tf.vocabulary_score) as avg_vocabulary,
                    AVG(tf.grammar_score) as avg_grammar,
                    AVG(tf.overall_score) as avg_overall
                FROM turns t
                LEFT JOIN turn_feedback tf ON t.turn_id = tf.turn_id
                WHERE t.conversation_id = %s
                """,
                (conversation_id,)
            )
            stats = cursor.fetchone()
        
        # 에러 통계
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    (SELECT COUNT(*) FROM pronunciation_errors pe JOIN turns t ON pe.turn_id = t.turn_id WHERE t.conversation_id = %s) as pronunciation_errors,
                    (SELECT COUNT(*) FROM vocabulary_errors ve JOIN turns t ON ve.turn_id = t.turn_id WHERE t.conversation_id = %s) as vocabulary_errors,
                    (SELECT COUNT(*) FROM grammar_errors ge JOIN turns t ON ge.turn_id = t.turn_id WHERE t.conversation_id = %s) as grammar_errors
                """,
                (conversation_id, conversation_id, conversation_id)
            )
            errors = cursor.fetchone()
        
        summary_text = f"Great conversation! You completed {stats['total_turns']} turns. "
        summary_text += f"Your average overall score was {stats['avg_overall']:.1f}. Keep practicing!"
        
        return EndConversationResponse(
            conversation_id=conversation_id,
            total_turns=stats['total_turns'],
            ended_at=ended_at,
            summary_text=summary_text,
            average_scores={
                "pronunciation": float(stats['avg_pronunciation'] or 0),
                "vocabulary": float(stats['avg_vocabulary'] or 0),
                "grammar": float(stats['avg_grammar'] or 0),
                "overall": float(stats['avg_overall'] or 0)
            },
            total_errors={
                "pronunciation": errors['pronunciation_errors'],
                "vocabulary": errors['vocabulary_errors'],
                "grammar": errors['grammar_errors']
            }
        )


# 싱글톤 인스턴스
conversation_service = ConversationService()
