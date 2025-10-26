# import google.generativeai as genai

from google import genai
from google.genai import types

from typing import List
import json
from app.config import get_settings
from app.models import AzurePronunciationResult, GeminiFeedbackResult

settings = get_settings()


class GeminiService:
    def __init__(self):
        # Create a genai client instance using the provided API key
        # This follows the pattern: client = genai.Client(api_key=...)
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    def generate_comprehensive_feedback(
        self,
        user_text: str,
        azure_results: List[AzurePronunciationResult]
    ) -> GeminiFeedbackResult:
        """
        Azure 발음 평가 결과를 바탕으로 종합 피드백 생성
        
        Args:
            user_text: 사용자가 말한 전체 텍스트
            azure_results: Azure로부터 받은 문장별 평가 결과
            
        Returns:
            GeminiFeedbackResult: 종합 피드백
        """
        # Azure 결과 요약
        azure_summary = []
        for result in azure_results:
            azure_summary.append({
                "sentence": result.text,
                "recognized": result.recognized_text,
                "pronunciation_score": result.pronunciation_score,
                "accuracy_score": result.accuracy_score,
                "fluency_score": result.fluency_score,
                "completeness_score": result.completeness_score,
                "errors": [{"word": e.word, "error_type": e.error_type, "accuracy": e.accuracy_score} for e in result.errors]
            })
        
        # 프롬프트 생성
        prompt = f"""You are an English pronunciation and grammar coach. Analyze the following speech and provide comprehensive feedback.

User's speech: "{user_text}"

Azure Pronunciation Assessment Results:
{json.dumps(azure_summary, indent=2)}

Please provide feedback in the following JSON format:
{{
    "pronunciation_score": <0-100>,
    "vocabulary_score": <0-100>,
    "grammar_score": <0-100>,
    "fluency_score": <0-100>,
    "overall_score": <0-100>,
    "overall_comment": "<brief overall assessment>",
    "strengths": {{
        "pronunciation": ["<strength1>", "<strength2>"],
        "vocabulary": ["<strength1>"],
        "grammar": ["<strength1>"],
        "fluency": ["<strength1>"]
    }},
    "improvements": {{
        "pronunciation": ["<improvement1>", "<improvement2>"],
        "vocabulary": ["<improvement1>"],
        "grammar": ["<improvement1>"],
        "fluency": ["<improvement1>"]
    }},
    "vocabulary_errors": [
        {{
            "incorrect_phrase": "<phrase>",
            "correct_phrase": "<correction>",
            "explanation": "<why>"
        }}
    ],
    "grammar_errors": [
        {{
            "incorrect_text": "<text>",
            "correct_text": "<correction>",
            "rule_violated": "<grammar rule>",
            "explanation": "<why>"
        }}
    ]
}}

Focus on:
1. Pronunciation issues from Azure assessment
2. Vocabulary appropriateness and word choice
3. Grammar correctness
4. Overall fluency and naturalness

Be encouraging but honest. Provide actionable feedback."""

        try:
            # Use the newer client API to generate content
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    top_k=1
                )
            )

            # JSON 파싱: SDK response shapes vary; extract text defensively
            response_text = self._extract_response_text(response).strip()
            
            # JSON 마크다운 제거
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            feedback_data = json.loads(response_text.strip())
            
            return GeminiFeedbackResult(**feedback_data)
            
        except Exception as e:
            print(f"Gemini feedback generation error: {e}")
            # 에러 시 기본 피드백 반환
            avg_pronunciation = sum(r.pronunciation_score for r in azure_results) / len(azure_results) if azure_results else 0
            
            return GeminiFeedbackResult(
                pronunciation_score=avg_pronunciation,
                vocabulary_score=70.0,
                grammar_score=70.0,
                fluency_score=70.0,
                overall_score=(avg_pronunciation + 70 + 70 + 70) / 4,
                overall_comment="Good effort! Keep practicing.",
                strengths={"pronunciation": [], "vocabulary": [], "grammar": [], "fluency": []},
                improvements={"pronunciation": [], "vocabulary": [], "grammar": [], "fluency": []},
                vocabulary_errors=[],
                grammar_errors=[]
            )
    
    def generate_conversation_response(self, user_text: str, conversation_history: List[dict] = None) -> str:
        """
        사용자 발화에 대한 자연스러운 대화 응답 생성
        
        Args:
            user_text: 사용자가 말한 텍스트
            conversation_history: 이전 대화 이력
            
        Returns:
            str: LLM의 응답
        """
        if conversation_history is None:
            conversation_history = []
        
        # 대화 히스토리 구성
        history_text = "\n".join([
            f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in conversation_history[-5:]  # 최근 5턴만
        ])
        
        prompt = f"""You are a friendly English conversation partner. Continue the conversation naturally.

Previous conversation:
{history_text}

User: {user_text}

Respond naturally and engagingly. Keep your response concise (1-3 sentences). Ask follow-up questions if appropriate."""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0, top_k=1)
            )
            return self._extract_response_text(response).strip()
        except Exception as e:
            print(f"Gemini conversation response error: {e}")
            return "That's interesting! Could you tell me more about it?"
    
    def generate_welcome_message(self, topic: str = None) -> str:
        """
        대화 시작 시 환영 메시지 생성
        
        Args:
            topic: 대화 주제 (optional)
            
        Returns:
            str: 환영 메시지
        """
        if topic:
            prompt = f"Generate a warm, friendly greeting for starting an English conversation about '{topic}'. Keep it brief (1-2 sentences)."
        else:
            prompt = "Generate a warm, friendly greeting for starting an English conversation practice. Keep it brief (1-2 sentences)."
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0, top_k=1)
            )
            return self._extract_response_text(response).strip()
        except Exception as e:
            print(f"Gemini welcome message error: {e}")
            return "Hello! I'm excited to practice English with you today. What would you like to talk about?"

    def _extract_response_text(self, response) -> str:
        """
        Try several common response shapes returned by the GenAI client and
        extract a textual answer. Falls back to str(response).
        """
        try:
            # common newer shape: response.output[0].content[0].text
            out = getattr(response, 'output', None)
            if out and isinstance(out, list) and len(out) > 0:
                content = out[0].get('content') if isinstance(out[0], dict) else getattr(out[0], 'content', None)
                if content and isinstance(content, list) and len(content) > 0:
                    first = content[0]
                    # dict-like
                    if isinstance(first, dict) and 'text' in first:
                        return first['text']
                    # object-like
                    if hasattr(first, 'text'):
                        return getattr(first, 'text')

            # other possible shapes
            if hasattr(response, 'content'):
                c = getattr(response, 'content')
                if isinstance(c, list) and len(c) > 0 and hasattr(c[0], 'text'):
                    return c[0].text

            if hasattr(response, 'text'):
                return getattr(response, 'text')

            # dict-like fallback
            if isinstance(response, dict):
                # try common keys
                for key in ('text', 'output_text', 'response'):
                    if key in response:
                        return response[key]

        except Exception:
            pass
        # final fallback
        return str(response)


# 싱글톤 인스턴스
gemini_service = GeminiService()
