import json
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.services.task_service import TaskService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/tasks", tags=["任务"])


# ---------- 请求模型 ----------

class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    steps: list[str] = Field(..., min_length=1, description="步骤列表")
    icon: str | None = Field(None, description="图标")
    is_public: bool = Field(True, description="是否公开")


class ToggleStepRequest(BaseModel):
    step_index: int = Field(..., ge=0, description="步骤索引")


class CreateUserTaskRequest(BaseModel):
    template_id: int = Field(..., description="模板 ID")


# ---------- 接口 ----------

@router.get("/templates")
def get_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取任务模板列表"""
    templates = TaskService.get_templates(db, is_public=True)
    result = []
    for t in templates:
        result.append({
            "id": t.id,
            "name": t.name,
            "icon": t.icon,
            "steps": json.loads(t.steps) if t.steps else [],
            "created_by": t.created_by,
            "is_public": t.is_public,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return {"code": 0, "message": "success", "data": result}


@router.post("/templates")
def create_template(
    req: CreateTemplateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("counselor", "admin")),
):
    """创建任务模板（辅导员/管理员）"""
    try:
        template = TaskService.create_template(
            db,
            name=req.name,
            steps=req.steps,
            icon=req.icon,
            created_by=current_user.id,
            is_public=req.is_public,
        )
        # 记录审计日志
        client_ip = request.client.host if request.client else None
        AuditService.log_action(
            db=db,
            user_id=current_user.id,
            action="create",
            resource="template",
            resource_id=template.id,
            detail={"name": req.name, "steps": req.steps},
            ip_address=client_ip,
        )
        return {
            "code": 0,
            "message": "创建成功",
            "data": {
                "id": template.id,
                "name": template.name,
                "icon": template.icon,
                "steps": json.loads(template.steps) if template.steps else [],
                "is_public": template.is_public,
            },
        }
    except ValueError as e:
        return {"code": 400, "message": str(e), "data": None}


@router.post("/my")
def create_my_task(
    req: CreateUserTaskRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建我的任务"""
    try:
        user_task = TaskService.create_user_task(db, current_user.id, req.template_id)
        # 记录审计日志
        client_ip = request.client.host if request.client else None
        AuditService.log_action(
            db=db,
            user_id=current_user.id,
            action="create",
            resource="task",
            resource_id=user_task.id,
            detail={"template_id": req.template_id},
            ip_address=client_ip,
        )
        return {
            "code": 0,
            "message": "任务创建成功",
            "data": {
                "id": user_task.id,
                "template_id": user_task.template_id,
                "status": user_task.status,
                "completed_steps": json.loads(user_task.completed_steps) if user_task.completed_steps else [],
            },
        }
    except ValueError as e:
        return {"code": 400, "message": str(e), "data": None}


@router.get("/my")
def get_my_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取我的任务列表"""
    tasks = TaskService.get_my_tasks(db, current_user.id)
    result = []
    for t in tasks:
        template_info = None
        if t.template:
            template_info = {
                "id": t.template.id,
                "name": t.template.name,
                "icon": t.template.icon,
                "steps": json.loads(t.template.steps) if t.template.steps else [],
            }
        result.append({
            "id": t.id,
            "template": template_info,
            "completed_steps": json.loads(t.completed_steps) if t.completed_steps else [],
            "status": t.status,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return {"code": 0, "message": "success", "data": result}


@router.post("/{task_id}/step")
def toggle_step(
    task_id: int,
    req: ToggleStepRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """完成/取消某个步骤"""
    try:
        user_task = TaskService.toggle_step(db, current_user.id, task_id, req.step_index)
        # 记录审计日志
        client_ip = request.client.host if request.client else None
        AuditService.log_action(
            db=db,
            user_id=current_user.id,
            action="update",
            resource="task",
            resource_id=task_id,
            detail={"step_index": req.step_index, "status": user_task.status},
            ip_address=client_ip,
        )
        return {
            "code": 0,
            "message": "操作成功",
            "data": {
                "id": user_task.id,
                "completed_steps": json.loads(user_task.completed_steps) if user_task.completed_steps else [],
                "status": user_task.status,
                "completed_at": user_task.completed_at.isoformat() if user_task.completed_at else None,
            },
        }
    except ValueError as e:
        return {"code": 400, "message": str(e), "data": None}
