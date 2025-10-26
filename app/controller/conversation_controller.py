from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from uuid import UUID
from pathlib import Path
import shutil

from app.models import (
    StartConversationRequest,
    StartConversationResponse,
    GenerateTranscriptionResponse,
    EndConversationResponse
)
from app.service.conversation_service import conversation_service
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/v1", tags=["conversation"])


@router.post("/conversations", response_model=StartConversationResponse)
async def start_conversation(request: StartConversationRequest):
    """
    새로운 대화 세션 시작
    
    - **user_id**: 사용자 ID
    - **topic**: 대화 주제 (optional)
    
    Returns:
        - conversation_id: 생성된 대화 ID
        - welcome_message_text: 환영 메시지
        - welcome_message_audio_url: 환영 메시지 음성 파일 경로
    """
    try:
        response = conversation_service.start_conversation(
            user_id=request.user_id,
            topic=request.topic
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start conversation: {str(e)}")


@router.post("/conversations/{conversation_id}/turns", response_model=GenerateTranscriptionResponse)
async def generate_transcription(
    conversation_id: UUID,
    turn_number: int = Form(...),
    audio_file: UploadFile = File(...)
):
    """
    턴 처리: 음성 → STT → 발음평가 → 피드백 생성 → 대화 응답
    
    - **conversation_id**: 대화 ID (path parameter)
    - **turn_number**: 턴 번호
    - **audio_file**: 사용자 음성 파일 (WAV)
    
    Returns:
        - 사용자 텍스트
        - 피드백 (점수, 코멘트, 문장별 상세)
        - 피드백 음성
        - LLM 응답 텍스트 및 음성
    """
    try:
        # 오디오 파일 저장
        audio_storage = Path(settings.AUDIO_STORAGE_PATH)
        audio_storage.mkdir(parents=True, exist_ok=True)
        
        audio_file_path = audio_storage / f"{conversation_id}_turn{turn_number}.wav"
        
        with open(audio_file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        
        # 턴 처리
        response = await conversation_service.process_turn(
            conversation_id=conversation_id,
            turn_number=turn_number,
            audio_file_path=str(audio_file_path)
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process turn: {str(e)}")


@router.post("/conversations/{conversation_id}/end", response_model=EndConversationResponse)
async def end_conversation(conversation_id: UUID):
    """
    대화 종료 및 요약
    
    - **conversation_id**: 대화 ID
    
    Returns:
        - 총 턴 수
        - 평균 점수
        - 총 에러 수
        - 요약 텍스트
    """
    try:
        # response = conversation_service.end_conversation(conversation_id)
        response = await conversation_service.end_conversation(
            conversation_id=conversation_id
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end conversation: {str(e)}")


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: UUID):
    """
    대화 정보 조회
    
    - **conversation_id**: 대화 ID
    """
    try:
        from app.database import db
        
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    c.*,
                    COUNT(t.turn_id) as total_turns,
                    AVG(tf.overall_score) as avg_score
                FROM conversations c
                LEFT JOIN turns t ON c.conversation_id = t.conversation_id
                LEFT JOIN turn_feedback tf ON t.turn_id = tf.turn_id
                WHERE c.conversation_id = %s
                GROUP BY c.conversation_id
                """,
                (conversation_id,)
            )
            conversation = cursor.fetchone()
            
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            return dict(conversation)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")


@router.get("/conversations/{conversation_id}/turns")
async def get_turns(conversation_id: UUID):
    """
    대화의 모든 턴 조회
    
    - **conversation_id**: 대화 ID
    """
    try:
        from app.database import db
        
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    t.*,
                    tf.pronunciation_score,
                    tf.vocabulary_score,
                    tf.grammar_score,
                    tf.overall_score,
                    tf.overall_comment
                FROM turns t
                LEFT JOIN turn_feedback tf ON t.turn_id = tf.turn_id
                WHERE t.conversation_id = %s
                ORDER BY t.turn_number
                """,
                (conversation_id,)
            )
            turns = cursor.fetchall()
            
            return [dict(turn) for turn in turns]
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get turns: {str(e)}")


@router.get("/users/{user_id}/conversations")
async def get_user_conversations(user_id: UUID):
    """
    사용자의 모든 대화 조회
    
    - **user_id**: 사용자 ID
    """
    try:
        from app.database import db
        
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    c.*,
                    COUNT(t.turn_id) as total_turns,
                    AVG(tf.overall_score) as avg_score
                FROM conversations c
                LEFT JOIN turns t ON c.conversation_id = t.conversation_id
                LEFT JOIN turn_feedback tf ON t.turn_id = tf.turn_id
                WHERE c.user_id = %s
                GROUP BY c.conversation_id
                ORDER BY c.started_at DESC
                """,
                (user_id,)
            )
            conversations = cursor.fetchall()
            
            return [dict(conv) for conv in conversations]
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversations: {str(e)}")
