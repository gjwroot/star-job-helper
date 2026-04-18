from sqlalchemy.orm import Session

from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token


class AuthService:
    """认证服务"""

    @staticmethod
    def register(db: Session, phone: str, name: str, password: str, role: str = "user") -> User:
        """用户注册"""
        # 检查手机号是否已注册
        existing_user = db.query(User).filter(User.phone == phone).first()
        if existing_user:
            raise ValueError("该手机号已注册")

        user = User(
            phone=phone,
            name=name,
            hashed_password=hash_password(password),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def login(db: Session, phone: str, password: str) -> dict:
        """用户登录，返回 token 和用户信息"""
        user = db.query(User).filter(User.phone == phone).first()
        if user is None or not verify_password(password, user.hashed_password):
            raise ValueError("手机号或密码错误")

        token = create_access_token(data={"sub": str(user.id), "role": user.role})
        return {
            "token": token,
            "token_type": "Bearer",
            "user": {
                "id": user.id,
                "phone": user.phone,
                "name": user.name,
                "role": user.role,
                "avatar": user.avatar,
            },
        }
