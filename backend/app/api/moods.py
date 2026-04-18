import json

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.mood_service import MoodService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/moods", tags=["情绪"])


# ---------- 请求模型 ----------

class MoodRecordRequest(BaseModel):
    mood_type: str = Field(..., description="情绪类型: happy/calm/anxious/sad/angry")


# ---------- 接口 ----------

@router.post("/record")
def record_mood(
    req: MoodRecordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """记录情绪"""
    try:
        record = MoodService.record_mood(db, current_user.id, req.mood_type)
        # 记录审计日志
        client_ip = request.client.host if request.client else None
        AuditService.log_action(
            db=db,
            user_id=current_user.id,
            action="create",
            resource="mood",
            resource_id=record.id,
            detail={"mood_type": req.mood_type},
            ip_address=client_ip,
        )
        return {
            "code": 0,
            "message": "记录成功",
            "data": {
                "id": record.id,
                "mood_type": record.mood_type,
                "tips": json.loads(record.tips) if record.tips else [],
                "created_at": record.created_at.isoformat() if record.created_at else None,
            },
        }
    except ValueError as e:
        return {"code": 400, "message": str(e), "data": None}


@router.get("/history")
def get_mood_history(
    limit: int = Query(default=30, ge=1, le=100, description="返回条数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取情绪历史"""
    records = MoodService.get_history(db, current_user.id, limit)
    result = []
    for r in records:
        result.append({
            "id": r.id,
            "mood_type": r.mood_type,
            "tips": json.loads(r.tips) if r.tips else [],
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return {"code": 0, "message": "success", "data": result}
