from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.core.rate_limit import rate_limit

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ---------- 请求模型 ----------

class RegisterRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    name: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    password: str = Field(..., min_length=6, max_length=100, description="密码")


# ---------- 响应模型 ----------

class UserOut(BaseModel):
    id: int
    phone: str
    name: str
    role: str
    avatar: str | None = None

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    token: str
    token_type: str
    user: UserOut


# ---------- 接口 ----------

@router.post("/register")
@rate_limit(max_requests=5, window_seconds=60)
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """用户注册"""
    try:
        user = AuthService.register(db, phone=req.phone, name=req.name, password=req.password)
        # 记录审计日志
        client_ip = request.client.host if request.client else None
        AuditService.log_action(
            db=db,
            user_id=user.id,
            action="create",
            resource="user",
            resource_id=user.id,
            detail={"phone": req.phone, "name": req.name},
            ip_address=client_ip,
        )
        return {
            "code": 0,
            "message": "注册成功",
            "data": {
                "id": user.id,
                "phone": user.phone,
                "name": user.name,
                "role": user.role,
            },
        }
    except ValueError as e:
        return {"code": 400, "message": str(e), "data": None}


@router.post("/login")
@rate_limit(max_requests=5, window_seconds=60)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """用户登录"""
    try:
        result = AuthService.login(db, phone=req.phone, password=req.password)
        # 记录审计日志
        client_ip = request.client.host if request.client else None
        AuditService.log_action(
            db=db,
            user_id=result["user"]["id"],
            action="login",
            resource="user",
            resource_id=result["user"]["id"],
            detail={"phone": req.phone},
            ip_address=client_ip,
        )
        return {
            "code": 0,
            "message": "登录成功",
            "data": result,
        }
    except ValueError as e:
        return {"code": 400, "message": str(e), "data": None}
