import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    def __init__(self) -> None:
        self.api_key = settings.GEMINI_API_KEY
        self.model = "models/gemini-1.5-flash"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate_answer(self, question: str, context: str) -> str:
        """
        Sends the question and context to Gemini and gets the result.
        Enforces answering ONLY from the context using system instructions.
        """
        system_prompt = (
            "You are a helpful assistant.\n\n"
            "Answer ONLY from the provided context.\n\n"
            "If answer is unavailable say:\n"
            "\"I could not find the answer in the provided documents.\""
        )
        
        user_prompt = f"Context:\n{context}\n\nQuestion: {question}"
        
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": user_prompt}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": system_prompt}
                ]
            },
            "generationConfig": {
                "temperature": 0.0
            }
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                # Extract candidates content
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        answer = parts[0].get("text", "")
                        return answer.strip()
                
                return ""
        except Exception as e:
            logger.error(f"Gemini LLM generation failed: {e}")
            raise
