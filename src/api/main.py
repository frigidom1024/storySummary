from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import os
from src.config import Config
from src.api.routers import auth, users, books
from src.api.exceptions import AppException
from src.api.schemas.error import ErrorResponse

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Story Summary API",
    description="API for story summarization and narrative analysis",
    version="0.1.0"
)


# 注册全局异常处理器
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """处理自定义应用异常"""
    logger.warning(f"AppException: {exc.error_code} - {exc.message}", extra={"details": exc.details})
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details
        ).model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误"""
    logger.warning(f"ValidationError: {exc.errors()}")
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    field = ".".join(str(loc) for loc in first_error.get("loc", []))
    message = first_error.get("msg", "请求参数验证失败")

    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error_code="VALIDATION_ERROR",
            message=message,
            details={"field": field, "errors": errors}
        ).model_dump()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理 HTTP 异常"""
    logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code="HTTP_ERROR",
            message=exc.detail,
            details=None
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="服务器内部错误",
            details=None
        ).model_dump()
    )


# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(books.router, prefix="/api")

# 确保封面目录存在
os.makedirs("data/covers", exist_ok=True)
# 封面静态文件路由
app.mount("/api/covers", StaticFiles(directory="data/covers"), name="covers")


@app.get("/")
def root():
    return {"message": "Story Summary API", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
