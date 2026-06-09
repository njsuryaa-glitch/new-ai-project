import time
import uuid
import os
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import setup_logging, get_logger, request_id_var
from app.api.routes import health, documents, ask
from app.schemas.error import ErrorResponse, ErrorDetails

# 1. Initialize logging
setup_logging()
logger = get_logger(__name__)

# 2. Instantiate application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-grade AI Knowledge Assistant API supporting document RAG",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 3. Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 4. Add Logging & Request ID Middleware
@app.middleware("http")
async def logging_and_request_id_middleware(request: Request, call_next):
    # Generates a unique request id or pulls it from headers if provided
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    # Set request ID context variable so all logs in this thread capture it
    token = request_id_var.set(request_id)
    
    start_time = time.perf_counter()
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time_ms = (time.perf_counter() - start_time) * 1000.0
        
        # Inject Request ID header into response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"
        
        logger.info(
            f"Completed request: {request.method} {request.url.path} "
            f"| Status: {response.status_code} | Latency: {process_time_ms:.2f}ms"
        )
        return response
    except Exception as e:
        process_time_ms = (time.perf_counter() - start_time) * 1000.0
        logger.error(
            f"Request failed: {request.method} {request.url.path} "
            f"| Latency: {process_time_ms:.2f}ms | Error: {str(e)}",
            exc_info=True
        )
        # Re-raise to let the global exception handler deal with it
        raise
    finally:
        # Reset context variable token
        request_id_var.reset(token)


# 5. Global Exception Handlers

def make_error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """
    Helper to construct standard consistent error JSON payloads.
    """
    error_response = ErrorResponse(
        success=False,
        error=ErrorDetails(code=code, message=message)
    )
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles Pydantic request validation errors (422).
    """
    # Compile error details
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err["loc"])
        errors.append(f"Field '{loc}': {err['msg']}")
    
    message = "Request validation failed: " + "; ".join(errors)
    logger.warning(f"Validation Error on {request.method} {request.url.path}: {message}")
    return make_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message=message
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handles standard HTTPExceptions raised in endpoint routers.
    """
    status_code = exc.status_code
    message = exc.detail
    
    # Map status codes to specific requirement error codes
    code_mapping = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: "FILE_TOO_LARGE",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
        status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMIT",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_SERVER_ERROR",
    }
    
    code = code_mapping.get(status_code, "HTTP_ERROR")
    logger.warning(f"HTTP Exception ({status_code}) on {request.method} {request.url.path}: {message}")
    
    return make_error_response(status_code=status_code, code=code, message=message)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler for unhandled internal code errors (500).
    """
    logger.error(f"Unhandled system error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return make_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please try again later."
    )


# 6. Include Route Routers directly at root level as specified
app.include_router(health.router)
app.include_router(documents.router)
app.include_router(ask.router)

# 7. Mount frontend static assets at root as fallback
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

