"""自定义异常类"""
from typing import Optional, Any


class AppException(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Any] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class AuthenticationError(AppException):
    """认证错误 - 用户未登录或 token 无效"""

    def __init__(self, message: str = "认证失败", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            details=details
        )


class AuthorizationError(AppException):
    """授权错误 - 用户无权限访问资源"""

    def __init__(self, message: str = "无权访问此资源", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            details=details
        )


class NotFoundError(AppException):
    """资源不存在"""

    def __init__(self, resource: str = "资源", details: Optional[Any] = None):
        super().__init__(
            message=f"{resource}不存在",
            error_code="NOT_FOUND",
            status_code=404,
            details=details
        )


class ValidationError(AppException):
    """数据验证错误"""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )
        self.field = field


class ConflictError(AppException):
    """资源冲突 - 如用户名已存在"""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=409,
            details=details
        )


class FileTooLargeError(AppException):
    """文件过大"""

    def __init__(self, max_size: str = "50MB", details: Optional[Any] = None):
        super().__init__(
            message=f"文件大小超过限制，最大支持 {max_size}",
            error_code="FILE_TOO_LARGE",
            status_code=413,
            details=details
        )


class UnsupportedFileTypeError(AppException):
    """不支持的文件类型"""

    def __init__(self, supported_types: str = "epub, txt", details: Optional[Any] = None):
        super().__init__(
            message=f"不支持的文件类型，仅支持 {supported_types}",
            error_code="UNSUPPORTED_FILE_TYPE",
            status_code=400,
            details=details
        )


class InvalidFileError(AppException):
    """文件格式错误"""

    def __init__(self, message: str = "文件格式错误", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="INVALID_FILE",
            status_code=400,
            details=details
        )


class EncodingError(AppException):
    """编码错误"""

    def __init__(self, message: str = "文件编码错误", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="ENCODING_ERROR",
            status_code=400,
            details=details
        )
