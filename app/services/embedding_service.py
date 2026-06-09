import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        self.api_key = settings.GEMINI_API_KEY
        self.model = "models/gemini-embedding-001"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generates embedding for a single text chunk using Google Gemini API.
        """
        if not text:
            return [0.0] * 768

        url = f"{self.base_url}/{self.model}:embedContent?key={self.api_key}"
        payload = {
            "model": self.model,
            "content": {
                "parts": [
                    {"text": text}
                ]
            },
            "outputDimensionality": 768
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["embedding"]["values"]
        except Exception as e:
            logger.error(f"Gemini embedding generation failed: {e}")
            raise

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generates embeddings for a batch of text chunks.
        Splits text list into sub-batches of 100 to avoid request payload limits.
        """
        if not texts:
            return []

        embeddings: list[list[float]] = []
        batch_size = 100
        url = f"{self.base_url}/{self.model}:batchEmbedContents?key={self.api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                requests_payload = []
                for text in batch:
                    requests_payload.append({
                        "model": self.model,
                        "content": {
                            "parts": [
                                {"text": text}
                            ]
                        },
                        "outputDimensionality": 768
                    })
                
                payload = {"requests": requests_payload}

                try:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    
                    batch_embeddings = [emb["values"] for emb in data.get("embeddings", [])]
                    embeddings.extend(batch_embeddings)
                except Exception as e:
                    logger.error(f"Gemini batch embedding generation failed for index range {i}-{i+len(batch)}: {e}")
                    raise

        return embeddings
