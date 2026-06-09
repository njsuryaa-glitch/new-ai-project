from fastapi import APIRouter, Depends, status, HTTPException
from app.api.dependencies.providers import get_retrieval_service, get_llm_service
from app.core.security import verify_api_key, sanitize_input
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService
from app.schemas.ask import AskRequest, AskResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    tags=["qa"],
    dependencies=[Depends(verify_api_key)]
)


@router.post(
    "/ask",
    response_model=AskResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask Question"
)
async def ask_question(
    request: AskRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    llm_service: LLMService = Depends(get_llm_service)
) -> AskResponse:
    """
    Query the knowledge base with a question.
    Processes:
    1. Embeds question and performs similarity search on pgvector index.
    2. Builds the retrieval context and queries GPT-4o-mini to get a grounded answer.
    3. Returns the synthesized answer along with source document details and text segments.
    """
    # 1. Sanitize user input
    sanitized_question = sanitize_input(request.question)
    if not sanitized_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or whitespace only."
        )

    logger.info(f"Answering question: '{sanitized_question}'")

    # 2. Retrieve relevant document chunks
    try:
        sources = await retrieval_service.retrieve_relevant_chunks(sanitized_question, limit=5)
    except Exception as e:
        logger.error(f"Error during context retrieval: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve relevant context chunks."
        )

    # 3. If no chunks found, we can pass an empty context or handle it.
    # LLM service is instructed via system prompt to respond with a fallback message if context is empty.
    context_str = ""
    if sources:
        context_str = "\n\n".join([f"Source chunk:\n{item['chunk']}" for item in sources])
    else:
        logger.info("No relevant chunks retrieved from pgvector search.")

    # 4. Generate answer using LLM
    try:
        answer = await llm_service.generate_answer(sanitized_question, context_str)
    except Exception as e:
        logger.error(f"Error generating answer from LLM: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate answer from language model."
        )

    return AskResponse(
        answer=answer,
        sources=sources
    )
