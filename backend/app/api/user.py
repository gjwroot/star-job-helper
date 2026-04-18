import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.task import UserTask, DailyStats
from app.models.mood import MoodRecord
from app.models.achievement import Achievement
from app.models.audit_log import AuditLog
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["用户数据"])


# ==================== 数据导出 ====================

@router.get("/data-export")
def export_user_data(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    导出当前用户所有数据（JSON格式，GDPR合规）。
    包含：用户基本信息、任务记录、情绪记录、成就记录、每日统计。
    """
    user_id = current_user.id

    # 用户基本信息
    user_data = {
        "id": user.id,
        "phone": user.phone,
        "name": user.name,
        "role": user.role,
        "avatar": user.avatar,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }

    # 任务记录
    tasks = db.query(UserTask).filter(UserTask.user_id == user_id).all()
    tasks_data = []
    for t in tasks:
        tasks_data.append({
            "id": t.id,
            "template_id": t.template_id,
            "completed_steps": json.loads(t.completed_steps) if t.completed_steps else [],
            "status": t.status,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    # 情绪记录
    moods = db.query(MoodRecord).filter(MoodRecord.user_id == user_id).all()
    moods_data = []
    for m in moods:
        moods_data.append({
            "id": m.id,
            "mood_type": m.mood_type,
            "tips": json.loads(m.tips) if m.tips else [],
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })

    # 成就记录
    achievements = db.query(Achievement).filter(Achievement.user_id == user_id).all()
    achievements_data = []
    for a in achievements:
        achievements_data.append({
            "id": a.id,
            "achievement_id": a.achievement_id,
            "unlocked_at": a.unlocked_at.isoformat() if a.unlocked_at else None,
        })

    # 每日统计
    daily_stats = db.query(DailyStats).filter(DailyStats.user_id == user_id).all()
    daily_stats_data = []
    for s in daily_stats:
        daily_stats_data.append({
            "date": s.date,
            "tasks_completed": s.tasks_completed,
            "stars_earned": s.stars_earned,
            "moods_logged": s.moods_logged,
        })

    export_data = {
        "export_info": {
            "user_id": user_id,
            "exported_at": datetime.now().isoformat(),
            "format_version": "1.0",
        },
        "user": user_data,
        "tasks": tasks_data,
        "moods": moods_data,
        "achievements": achievements_data,
        "daily_stats": daily_stats_data,
    }

    # 记录审计日志
    client_ip = request.client.host if request.client else None
    AuditService.log_action(
        db=db,
        user_id=user_id,
        action="read",
        resource="user",
        resource_id=user_id,
        detail={"action": "data_export"},
        ip_address=client_ip,
    )

    return {
        "code": 0,
        "message": "数据导出成功",
        "data": export_data,
    }


# ==================== 账户注销 ====================

@router.delete("/account")
def deactivate_account(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    注销账户（软删除，标记 is_active=False）。
    账户数据保留30天，30天后可由系统自动清理。
    """
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查是否已有 is_active 字段，如果没有则使用备注方式标记
    # 为了兼容现有模型，使用 name 前缀标记
    if not hasattr(user, 'is_active'):
        # 软删除：在用户名前添加标记
        user.name = f"[已注销]_{user.name}"
        user.phone = f"deactivated_{user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    else:
        user.is_active = False

    db.commit()

    # 记录审计日志
    client_ip = request.client.host if request.client else None
    AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource="user",
        resource_id=current_user.id,
        detail={"action": "deactivate_account"},
        ip_address=client_ip,
    )

    return {
        "code": 0,
        "message": "账户已注销，数据将在30天后被永久删除",
        "data": {
            "user_id": current_user.id,
            "deactivated_at": datetime.now().isoformat(),
        },
    }


# ==================== 数据删除请求 ====================

class DataDeleteRequest(BaseModel):
    """数据删除请求"""
    reason: str | None = None  # 删除原因（可选）


@router.post("/data-delete-request")
def request_data_deletion(
    req: DataDeleteRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    请求数据删除（GDPR合规）。
    记录删除请求，7天后系统将自动执行数据删除。
    """
    # 记录审计日志作为删除请求记录
    client_ip = request.client.host if request.client else None
    AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource="user",
        resource_id=current_user.id,
        detail={
            "action": "data_delete_request",
            "reason": req.reason,
            "scheduled_delete_at": (
                datetime.now() + __import__('datetime').timedelta(days=7)
            ).isoformat(),
            "status": "pending",
        },
        ip_address=client_ip,
    )

    return {
        "code": 0,
        "message": "数据删除请求已提交，将在7天后执行删除",
        "data": {
            "user_id": current_user.id,
            "requested_at": datetime.now().isoformat(),
            "scheduled_delete_at": (
                datetime.now() + __import__('datetime').timedelta(days=7)
            ).isoformat(),
            "status": "pending",
        },
    }
