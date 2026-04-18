import json
import logging
import os
import shutil
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.models.task import UserTask, DailyStats, TaskTemplate
from app.models.mood import MoodRecord
from app.models.achievement import Achievement
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


# ==================== Schemas ====================

class RoleUpdateRequest(BaseModel):
    """修改用户角色请求"""
    role: str  # user / counselor / admin


class TaskTemplateCreateRequest(BaseModel):
    """创建任务模板请求"""
    name: str
    icon: Optional[str] = None
    steps: Optional[list] = None  # 步骤列表
    is_public: bool = True


class TaskTemplateUpdateRequest(BaseModel):
    """更新任务模板请求"""
    name: Optional[str] = None
    icon: Optional[str] = None
    steps: Optional[list] = None
    is_public: Optional[bool] = None


class RestoreRequest(BaseModel):
    """恢复备份请求"""
    backup_file: str  # 备份文件名


# ==================== 用户管理 ====================

@router.get("/users")
def get_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    role: Optional[str] = Query(None, description="按角色筛选"),
    keyword: Optional[str] = Query(None, description="搜索关键词（姓名/手机号）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "counselor")),
):
    """获取用户列表（支持分页、筛选、搜索）"""
    query = db.query(User)

    # 角色筛选
    if role:
        query = query.filter(User.role == role)

    # 关键词搜索
    if keyword:
        query = query.filter(
            (User.name.contains(keyword)) | (User.phone.contains(keyword))
        )

    # 总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

    result = []
    for u in users:
        # 统计该用户的任务完成数
        completed_count = db.query(func.count(UserTask.id)).filter(
            UserTask.user_id == u.id,
            UserTask.status == "completed",
        ).scalar() or 0

        # 统计情绪记录数
        mood_count = db.query(func.count(MoodRecord.id)).filter(
            MoodRecord.user_id == u.id,
        ).scalar() or 0

        result.append({
            "id": u.id,
            "phone": u.phone,
            "name": u.name,
            "role": u.role,
            "avatar": u.avatar,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "tasks_completed": completed_count,
            "mood_count": mood_count,
        })

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": result,
        },
    }


@router.get("/users/{user_id}")
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "counselor")),
):
    """获取用户详情"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 任务统计
    total_tasks = db.query(func.count(UserTask.id)).filter(
        UserTask.user_id == user.id
    ).scalar() or 0
    completed_tasks = db.query(func.count(UserTask.id)).filter(
        UserTask.user_id == user.id,
        UserTask.status == "completed",
    ).scalar() or 0

    # 情绪统计
    total_moods = db.query(func.count(MoodRecord.id)).filter(
        MoodRecord.user_id == user.id
    ).scalar() or 0

    # 成就统计
    total_achievements = db.query(func.count(Achievement.id)).filter(
        Achievement.user_id == user.id
    ).scalar() or 0

    # 最近7天每日统计
    seven_days_ago = (date.today() - timedelta(days=6)).isoformat()
    daily_stats = (
        db.query(DailyStats)
        .filter(
            DailyStats.user_id == user.id,
            DailyStats.date >= seven_days_ago,
        )
        .order_by(DailyStats.date)
        .all()
    )
    weekly_trend = [
        {
            "date": s.date,
            "tasks_completed": s.tasks_completed,
            "stars_earned": s.stars_earned,
            "moods_logged": s.moods_logged,
        }
        for s in daily_stats
    ]

    # 最近情绪记录
    recent_moods = (
        db.query(MoodRecord)
        .filter(MoodRecord.user_id == user.id)
        .order_by(MoodRecord.created_at.desc())
        .limit(10)
        .all()
    )
    mood_list = [
        {
            "id": m.id,
            "mood_type": m.mood_type,
            "tips": m.tips,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in recent_moods
    ]

    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": user.id,
            "phone": user.phone,
            "name": user.name,
            "role": user.role,
            "avatar": user.avatar,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "stats": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "total_moods": total_moods,
                "total_achievements": total_achievements,
            },
            "weekly_trend": weekly_trend,
            "recent_moods": mood_list,
        },
    }


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    req: RoleUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """修改用户角色（仅管理员）"""
    if req.role not in ("user", "counselor", "admin"):
        raise HTTPException(status_code=400, detail="无效的角色值，可选: user, counselor, admin")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    old_role = user.role
    user.role = req.role
    db.commit()
    db.refresh(user)

    # 记录审计日志
    client_ip = request.client.host if request.client else None
    AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="update",
        resource="user",
        resource_id=user_id,
        detail={"old_role": old_role, "new_role": req.role},
        ip_address=client_ip,
    )

    return {
        "code": 0,
        "message": f"角色已从 {old_role} 修改为 {req.role}",
        "data": {
            "id": user.id,
            "name": user.name,
            "role": user.role,
        },
    }


# ==================== 全局统计 ====================

@router.get("/stats")
def get_global_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "counselor")),
):
    """获取全局统计"""
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_tasks_completed = db.query(func.count(UserTask.id)).filter(
        UserTask.status == "completed"
    ).scalar() or 0
    total_moods = db.query(func.count(MoodRecord.id)).scalar() or 0
    total_achievements = db.query(func.count(Achievement.id)).scalar() or 0

    # 今日统计
    today = date.today().isoformat()
    today_stats = db.query(DailyStats).filter(DailyStats.date == today).all()
    today_tasks = sum(s.tasks_completed for s in today_stats)
    today_moods = sum(s.moods_logged for s in today_stats)
    today_active_users = len(set(s.user_id for s in today_stats))

    # 最近7天趋势
    seven_days_ago = (date.today() - timedelta(days=6)).isoformat()
    weekly_stats = (
        db.query(DailyStats)
        .filter(DailyStats.date >= seven_days_ago)
        .order_by(DailyStats.date)
        .all()
    )
    # 按日期聚合
    from collections import defaultdict
    daily_agg = defaultdict(lambda: {"tasks_completed": 0, "stars_earned": 0, "moods_logged": 0})
    for s in weekly_stats:
        daily_agg[s.date]["tasks_completed"] += s.tasks_completed
        daily_agg[s.date]["stars_earned"] += s.stars_earned
        daily_agg[s.date]["moods_logged"] += s.moods_logged

    weekly_trend = [
        {"date": d, **daily_agg[d]}
        for d in sorted(daily_agg.keys())
    ]

    # 最近30天每日新增用户数
    thirty_days_ago = (date.today() - timedelta(days=29)).isoformat()
    user_registrations = (
        db.query(
            func.date(User.created_at).label("reg_date"),
            func.count(User.id).label("count"),
        )
        .filter(func.date(User.created_at) >= thirty_days_ago)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
        .all()
    )
    registration_trend = [
        {"date": str(r.reg_date), "new_users": r.count}
        for r in user_registrations
    ]

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total_users": total_users,
            "total_tasks_completed": total_tasks_completed,
            "total_moods": total_moods,
            "total_achievements": total_achievements,
            "today": {
                "tasks_completed": today_tasks,
                "moods_logged": today_moods,
                "active_users": today_active_users,
            },
            "weekly_trend": weekly_trend,
            "registration_trend": registration_trend,
        },
    }


# ==================== 情绪统计 ====================

@router.get("/mood-stats")
def get_mood_stats(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "counselor")),
):
    """情绪统计（各情绪类型分布）"""
    from datetime import timedelta as td

    since = (date.today() - td(days=days - 1)).isoformat()

    # 各情绪类型数量
    mood_distribution = (
        db.query(MoodRecord.mood_type, func.count(MoodRecord.id))
        .filter(func.date(MoodRecord.created_at) >= since)
        .group_by(MoodRecord.mood_type)
        .all()
    )

    total = sum(count for _, count in mood_distribution)

    distribution = []
    mood_labels = {
        "happy": "开心",
        "calm": "平静",
        "anxious": "焦虑",
        "sad": "难过",
        "angry": "生气",
    }
    for mood_type, count in mood_distribution:
        distribution.append({
            "mood_type": mood_type,
            "label": mood_labels.get(mood_type, mood_type),
            "count": count,
            "percentage": round(count / total * 100, 1) if total > 0 else 0,
        })

    # 按日期统计情绪趋势
    daily_mood_trend = (
        db.query(
            func.date(MoodRecord.created_at).label("mood_date"),
            MoodRecord.mood_type,
            func.count(MoodRecord.id).label("count"),
        )
        .filter(func.date(MoodRecord.created_at) >= since)
        .group_by(func.date(MoodRecord.created_at), MoodRecord.mood_type)
        .order_by(func.date(MoodRecord.created_at))
        .all()
    )

    # 按日期聚合
    from collections import defaultdict
    daily_mood = defaultdict(lambda: {})
    for row in daily_mood_trend:
        daily_mood[str(row.mood_date)][row.mood_type] = row.count

    trend = [
        {"date": d, **daily_mood[d]}
        for d in sorted(daily_mood.keys())
    ]

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total_records": total,
            "period_days": days,
            "distribution": distribution,
            "daily_trend": trend,
        },
    }


# ==================== 任务模板管理 ====================

@router.get("/task-templates")
def get_task_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_public: Optional[bool] = Query(None, description="是否公开"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "counselor")),
):
    """获取任务模板列表"""
    query = db.query(TaskTemplate)

    if is_public is not None:
        query = query.filter(TaskTemplate.is_public == is_public)

    total = query.count()
    offset = (page - 1) * page_size
    templates = query.order_by(TaskTemplate.created_at.desc()).offset(offset).limit(page_size).all()

    items = []
    for t in templates:
        steps = []
        if t.steps:
            try:
                steps = json.loads(t.steps)
            except (json.JSONDecodeError, TypeError):
                steps = []

        # 统计使用该模板的任务数
        usage_count = db.query(func.count(UserTask.id)).filter(
            UserTask.template_id == t.id
        ).scalar() or 0

        items.append({
            "id": t.id,
            "name": t.name,
            "icon": t.icon,
            "steps": steps,
            "is_public": t.is_public,
            "created_by": t.created_by,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "usage_count": usage_count,
        })

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        },
    }


@router.post("/task-templates")
def create_task_template(
    req: TaskTemplateCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "counselor")),
):
    """创建全局任务模板"""
    template = TaskTemplate(
        name=req.name,
        icon=req.icon,
        steps=json.dumps(req.steps, ensure_ascii=False) if req.steps else None,
        is_public=req.is_public,
        created_by=current_user.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    # 记录审计日志
    client_ip = request.client.host if request.client else None
    AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="create",
        resource="template",
        resource_id=template.id,
        detail={"name": req.name},
        ip_address=client_ip,
    )

    return {
        "code": 0,
        "message": "模板创建成功",
        "data": {
            "id": template.id,
            "name": template.name,
            "icon": template.icon,
            "steps": json.loads(template.steps) if template.steps else [],
            "is_public": template.is_public,
            "created_by": template.created_by,
            "created_at": template.created_at.isoformat() if template.created_at else None,
        },
    }


@router.put("/task-templates/{template_id}")
def update_task_template(
    template_id: int,
    req: TaskTemplateUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """更新任务模板（仅管理员）"""
    template = db.query(TaskTemplate).filter(TaskTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    changes = {}
    if req.name is not None:
        changes["name"] = {"old": template.name, "new": req.name}
        template.name = req.name
    if req.icon is not None:
        changes["icon"] = {"old": template.icon, "new": req.icon}
        template.icon = req.icon
    if req.steps is not None:
        changes["steps"] = {"old": template.steps, "new": json.dumps(req.steps, ensure_ascii=False)}
        template.steps = json.dumps(req.steps, ensure_ascii=False)
    if req.is_public is not None:
        changes["is_public"] = {"old": template.is_public, "new": req.is_public}
        template.is_public = req.is_public

    db.commit()
    db.refresh(template)

    # 记录审计日志
    client_ip = request.client.host if request.client else None
    AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="update",
        resource="template",
        resource_id=template_id,
        detail=changes,
        ip_address=client_ip,
    )

    return {
        "code": 0,
        "message": "模板更新成功",
        "data": {
            "id": template.id,
            "name": template.name,
            "icon": template.icon,
            "steps": json.loads(template.steps) if template.steps else [],
            "is_public": template.is_public,
            "created_at": template.created_at.isoformat() if template.created_at else None,
        },
    }


@router.delete("/task-templates/{template_id}")
def delete_task_template(
    template_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """删除任务模板（仅管理员）"""
    template = db.query(TaskTemplate).filter(TaskTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 检查是否有用户正在使用此模板
    active_tasks = db.query(func.count(UserTask.id)).filter(
        UserTask.template_id == template_id,
        UserTask.status == "in_progress",
    ).scalar() or 0

    if active_tasks > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该模板仍有 {active_tasks} 个进行中的任务，无法删除",
        )

    db.delete(template)
    db.commit()

    # 记录审计日志
    client_ip = request.client.host if request.client else None
    AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource="template",
        resource_id=template_id,
        detail={"name": template.name},
        ip_address=client_ip,
    )

    return {
        "code": 0,
        "message": "模板已删除",
        "data": {"id": template_id},
    }


# ==================== 审计日志 ====================

@router.get("/audit-logs")
def get_audit_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: Optional[int] = Query(None, description="按用户ID筛选"),
    action: Optional[str] = Query(None, description="按操作类型筛选"),
    resource: Optional[str] = Query(None, description="按资源类型筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """查看审计日志（仅管理员）"""
    result = AuditService.get_audit_logs(
        db=db,
        user_id=user_id,
        action=action,
        resource=resource,
        page=page,
        page_size=page_size,
    )
    return {
        "code": 0,
        "message": "success",
        "data": result,
    }


# ==================== 数据备份 ====================

def _get_backup_dir() -> str:
    """获取备份目录路径"""
    from app.config import get_settings
    settings = get_settings()
    backup_dir = settings.DB_BACKUP_PATH
    if not os.path.isabs(backup_dir):
        # 相对于 backend 目录
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backup_dir = os.path.join(backend_dir, backup_dir)
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def _get_db_path() -> str:
    """获取数据库文件路径"""
    from app.config import get_settings
    settings = get_settings()
    db_url = settings.DATABASE_URL
    # 从 sqlite:///./star_job_helper.db 提取路径
    if db_url.startswith("sqlite:///"):
        db_path = db_url[len("sqlite:///"):]
        if not os.path.isabs(db_path):
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(backend_dir, db_path)
        return db_path
    raise ValueError("仅支持 SQLite 数据库备份")


@router.post("/backup")
def create_backup(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """手动触发数据库备份"""
    try:
        backup_dir = _get_backup_dir()
        db_path = _get_db_path()

        if not os.path.exists(db_path):
            raise HTTPException(status_code=500, detail="数据库文件不存在")

        filename = f"starjob_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = os.path.join(backup_dir, filename)

        shutil.copy2(db_path, backup_path)

        # 记录审计日志
        client_ip = request.client.host if request.client else None
        AuditService.log_action(
            db=db,
            user_id=current_user.id,
            action="create",
            resource="backup",
            detail={"filename": filename, "size": os.path.getsize(backup_path)},
            ip_address=client_ip,
        )

        logger.info(f"数据库备份已创建: {backup_path}")

        return {
            "code": 0,
            "message": "备份创建成功",
            "data": {
                "filename": filename,
                "path": backup_path,
                "size": os.path.getsize(backup_path),
                "created_at": datetime.now().isoformat(),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        raise HTTPException(status_code=500, detail=f"备份创建失败: {str(e)}")


@router.get("/backups")
def list_backups(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """列出所有备份文件"""
    try:
        backup_dir = _get_backup_dir()

        backups = []
        if os.path.exists(backup_dir):
            for filename in sorted(os.listdir(backup_dir), reverse=True):
                if filename.startswith("starjob_backup_") and filename.endswith(".db"):
                    filepath = os.path.join(backup_dir, filename)
                    stat = os.stat(filepath)
                    backups.append({
                        "filename": filename,
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })

        return {
            "code": 0,
            "message": "success",
            "data": {
                "total": len(backups),
                "items": backups,
            },
        }
    except Exception as e:
        logger.error(f"列出备份失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出备份失败: {str(e)}")


@router.post("/restore")
def restore_backup(
    req: RestoreRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """从备份恢复数据库"""
    try:
        backup_dir = _get_backup_dir()
        backup_path = os.path.join(backup_dir, req.backup_file)

        # 安全校验：确保文件名符合格式，防止路径遍历
        if not req.backup_file.startswith("starjob_backup_") or not req.backup_file.endswith(".db"):
            raise HTTPException(status_code=400, detail="无效的备份文件名")

        if not os.path.exists(backup_path):
            raise HTTPException(status_code=404, detail="备份文件不存在")

        db_path = _get_db_path()

        # 先创建当前数据库的备份（恢复前备份）
        pre_restore_filename = f"starjob_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        pre_restore_path = os.path.join(backup_dir, pre_restore_filename)
        if os.path.exists(db_path):
            shutil.copy2(db_path, pre_restore_path)

        # 执行恢复
        shutil.copy2(backup_path, db_path)

        # 记录审计日志
        client_ip = request.client.host if request.client else None
        AuditService.log_action(
            db=db,
            user_id=current_user.id,
            action="update",
            resource="backup",
            detail={
                "action": "restore",
                "backup_file": req.backup_file,
                "pre_restore_backup": pre_restore_filename,
            },
            ip_address=client_ip,
        )

        logger.info(f"数据库已从备份恢复: {req.backup_file}")

        return {
            "code": 0,
            "message": "数据库恢复成功，建议重启应用以使更改完全生效",
            "data": {
                "restored_from": req.backup_file,
                "pre_restore_backup": pre_restore_filename,
                "restored_at": datetime.now().isoformat(),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复备份失败: {e}")
        raise HTTPException(status_code=500, detail=f"恢复备份失败: {str(e)}")
