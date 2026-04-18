import json
import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """审计日志服务"""

    @staticmethod
    def log_action(
        db: Session,
        user_id: Optional[int] = None,
        action: str = "",
        resource: str = "",
        resource_id: Optional[int] = None,
        detail: Optional[dict | str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        记录审计日志。

        Args:
            db: 数据库会话
            user_id: 操作用户ID（None表示系统操作）
            action: 操作类型（login/logout/create/update/delete）
            resource: 资源类型（user/task/mood/achievement/template）
            resource_id: 资源ID
            detail: 操作详情（字典或字符串）
            ip_address: 客户端IP地址

        Returns:
            AuditLog: 创建的审计日志记录
        """
        # 将 detail 转换为 JSON 字符串
        if detail is not None and not isinstance(detail, str):
            try:
                detail = json.dumps(detail, ensure_ascii=False)
            except (TypeError, ValueError):
                detail = str(detail)

        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            detail=detail,
            ip_address=ip_address,
        )
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)

        logger.info(
            f"审计日志: user_id={user_id}, action={action}, "
            f"resource={resource}, resource_id={resource_id}"
        )

        return audit_log

    @staticmethod
    def get_audit_logs(
        db: Session,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """
        查询审计日志（管理员接口，支持筛选和分页）。

        Args:
            db: 数据库会话
            user_id: 按用户ID筛选
            action: 按操作类型筛选
            resource: 按资源类型筛选
            page: 页码
            page_size: 每页数量

        Returns:
            dict: 包含 total, page, page_size, items 的分页结果
        """
        query = db.query(AuditLog)

        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource:
            query = query.filter(AuditLog.resource == resource)

        total = query.count()
        offset = (page - 1) * page_size
        logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size).all()

        items = []
        for log in logs:
            detail_data = None
            if log.detail:
                try:
                    detail_data = json.loads(log.detail)
                except (json.JSONDecodeError, TypeError):
                    detail_data = log.detail

            items.append({
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource": log.resource,
                "resource_id": log.resource_id,
                "detail": detail_data,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            })

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        }

    @staticmethod
    def get_user_audit_logs(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """
        查询指定用户的操作日志。

        Args:
            db: 数据库会话
            user_id: 用户ID
            page: 页码
            page_size: 每页数量

        Returns:
            dict: 包含 total, page, page_size, items 的分页结果
        """
        return AuditService.get_audit_logs(
            db=db,
            user_id=user_id,
            page=page,
            page_size=page_size,
        )
