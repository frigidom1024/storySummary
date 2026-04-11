from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from src.api.schemas.user import UserResponse
from src.api.security import decode_token
from src.api.deps import get_user_service
from src.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """从 Authorization header 获取当前用户 ID"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")

    token = authorization[7:]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return user_id


@router.get("/me", response_model=UserResponse)
def get_me(
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """获取当前用户信息"""
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/me", response_model=UserResponse)
def update_me(
    profile: dict,
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """更新当前用户资料"""
    user = user_service.update_profile(user_id, profile)
    return user
