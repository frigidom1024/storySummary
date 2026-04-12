"""统一错误响应 Schema"""
from typing import Optional, Any
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """统一错误响应格式"""
    error_code: str
    message: str
    details: Optional[Any] = None

    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "NOT_FOUND",
                "message": "书籍不存在",
                "details": None
            }
        }


class ValidationErrorDetail(BaseModel):
    """验证错误详情"""
    field: Optional[str] = None
    message: str


class ValidationErrorResponse(ErrorResponse):
    """验证错误响应"""
    details: Optional[ValidationErrorDetail] = None
