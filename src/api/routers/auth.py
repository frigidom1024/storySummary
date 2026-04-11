from fastapi import APIRouter, HTTPException, Depends
from src.api.schemas.auth import Token, RegisterRequest, LoginRequest
from src.api.security import create_access_token
from src.api.deps import get_user_service
from src.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token)
def register(request: RegisterRequest, user_service: UserService = Depends(get_user_service)):
    # 检查用户名是否存在
    existing = user_service.get_user_by_username(request.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # 创建用户
    user = user_service.create_user(
        username=request.username,
        email=request.email,
        password=request.password
    )

    # 生成 Token
    access_token = create_access_token(data={"sub": user.id})
    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
def login(request: LoginRequest, user_service: UserService = Depends(get_user_service)):
    user = user_service.authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user.id})
    return Token(access_token=access_token)
