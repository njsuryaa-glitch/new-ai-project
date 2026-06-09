from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine
from fastapi import BackgroundTasks
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseQueue(ABC):
    @abstractmethod
    async def enqueue(self, func: Callable[..., Coroutine[Any, Any, Any]], *args: Any, **kwargs: Any) -> None:
        pass


class BackgroundTasksQueue(BaseQueue):
    """
    Queue abstraction using FastAPI's BackgroundTasks.
    Executes functions asynchronously in the background.
    """
    def __init__(self, background_tasks: BackgroundTasks) -> None:
        self.background_tasks = background_tasks

    async def enqueue(self, func: Callable[..., Coroutine[Any, Any, Any]], *args: Any, **kwargs: Any) -> None:
        logger.info(f"Enqueuing task: {func.__name__} in BackgroundTasks.")
        self.background_tasks.add_task(func, *args, **kwargs)


class RedisQueue(BaseQueue):
    """
    Redis list-based queue abstraction for horizontal worker scale.
    """
    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as aioredis
        self.redis_client = aioredis.from_url(redis_url)
        logger.info("Initialized Redis Queue client.")

    async def enqueue(self, func: Callable[..., Coroutine[Any, Any, Any]], *args: Any, **kwargs: Any) -> None:
        # Serializes tasks and pushes them to Redis list.
        # In production, a worker process (like celery or arq) polls and runs them.
        logger.info(f"Redis Queue: Enqueued job {func.__name__} (simulated via Redis list push).")
        # To make it out-of-the-box runnable, we will execute it directly if no external worker exists, 
        # or log the queue message. For local setup we fallback or print.
        import json
        try:
            job_payload = {
                "function": func.__name__,
                "args": [str(a) for a in args],
                "kwargs": {k: str(v) for k, v in kwargs.items()}
            }
            await self.redis_client.rpush("document_jobs", json.dumps(job_payload))
        except Exception as e:
            logger.error(f"Failed to push to Redis queue: {e}")
