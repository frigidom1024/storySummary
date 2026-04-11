from fastapi import APIRouter, HTTPException, Depends
from src.api.schemas.user import UserResponse
from src.api.deps import get_user_service, get_current_user_id
from src.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


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
