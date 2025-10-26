from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ============================================
# Request Models
# ============================================

class StartConversationRequest(BaseModel):
    user_id: UUID
    topic: Optional[str] = None


class GenerateTranscriptionRequest(BaseModel):
    conversation_id: UUID
    turn_number: int
    # 실제로는 audio_file을 multipart/form-data로 받음


class EndConversationRequest(BaseModel):
    conversation_id: UUID


# ============================================
# Response Models
# ============================================

class StartConversationResponse(BaseModel):
    conversation_id: UUID
    welcome_message_text: str
    welcome_message_audio_url: Optional[str] = None
    started_at: datetime


class SentenceScore(BaseModel):
    sentence_id: UUID
    sentence_number: int
    text: str
    accuracy_score: Optional[float] = None
    fluency_score: Optional[float] = None
    completeness_score: Optional[float] = None
    prosody_score: Optional[float] = None


class WordError(BaseModel):
    word: str
    phoneme: Optional[str] = None
    error_type: str
    accuracy_score: Optional[float] = None
    expected_phoneme: Optional[str] = None
    actual_phoneme: Optional[str] = None


class TurnFeedback(BaseModel):
    feedback_id: UUID
    turn_id: UUID
    
    # Scores
    pronunciation_score: Optional[float] = None
    vocabulary_score: Optional[float] = None
    grammar_score: Optional[float] = None
    fluency_score: Optional[float] = None
    overall_score: Optional[float] = None
    
    # Comments
    overall_comment: Optional[str] = None
    strengths: Optional[dict] = None
    improvements: Optional[dict] = None
    
    # Sentence details
    sentences: List[SentenceScore] = []
    
    # Errors
    pronunciation_errors: List[WordError] = []
    vocabulary_errors: List[dict] = []
    grammar_errors: List[dict] = []


class GenerateTranscriptionResponse(BaseModel):
    turn_id: UUID
    conversation_id: UUID
    turn_number: int
    
    # User's speech
    user_text: str
    user_audio_url: Optional[str] = None
    
    # Feedback
    feedback: TurnFeedback
    feedback_text: str  # TTS용 텍스트
    feedback_audio_url: Optional[str] = None
    
    # LLM's response (다음 대화)
    llm_response_text: str
    llm_response_audio_url: Optional[str] = None
    
    created_at: datetime


class EndConversationResponse(BaseModel):
    conversation_id: UUID
    total_turns: int
    ended_at: datetime
    
    # Summary
    summary_text: str
    average_scores: dict
    total_errors: dict


class GetFeedbackResponse(BaseModel):
    turn_id: UUID
    feedback: TurnFeedback


# ============================================
# Internal Models
# ============================================

class AzurePronunciationResult(BaseModel):
    sentence_id: UUID
    sentence_number: int
    text: str
    recognized_text: str
    
    # Scores
    pronunciation_score: float
    accuracy_score: float
    fluency_score: float
    completeness_score: float
    prosody_score: Optional[float] = None
    
    # Word-level details
    words: List[dict] = []
    errors: List[WordError] = []
    
    # Raw data
    azure_raw_data: dict


class GeminiFeedbackResult(BaseModel):
    # Overall scores (0-100)
    pronunciation_score: float
    vocabulary_score: float
    grammar_score: float
    fluency_score: float
    overall_score: float
    
    # Comments
    overall_comment: str
    strengths: dict  # {"pronunciation": [...], "vocabulary": [...], ...}
    improvements: dict
    
    # Detected errors
    vocabulary_errors: List[dict] = []
    grammar_errors: List[dict] = []
