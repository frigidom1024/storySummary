import uuid
import hashlib
from datetime import datetime
from typing import Optional
from src.models.user import User
from src.services.interfaces import IUserService
from src.storage.database import Database


class UserService(IUserService):
    def __init__(self, db: Database):
        self.db = db

    def create_user(self, username: str, email: str, password: str) -> User:
        """创建用户"""
        password_hash = self._hash_password(password)
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=password_hash,
            profile={},
            created_at=datetime.now()
        )
        self.db.create_user(user)
        return user

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.db.get_user_by_id(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.db.get_user_by_username(username)

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """验证用户"""
        user = self.db.get_user_by_username(username)
        if user and self._verify_password(password, user.password_hash):
            return user
        return None

    def update_profile(self, user_id: str, profile: dict) -> User:
        """更新用户资料"""
        self.db.update_user_profile(user_id, profile)
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        return user

    def _hash_password(self, password: str) -> str:
        """简单哈希密码（生产环境应使用 bcrypt）"""
        return hashlib.sha256(password.encode()).hexdigest()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        return self._hash_password(password) == password_hash