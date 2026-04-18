from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    """审计日志表"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 操作用户（None表示系统操作）
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # 操作类型：login/logout/create/update/delete
    resource: Mapped[str] = mapped_column(String(50), nullable=False)  # 资源类型：user/task/mood/achievement/template
    resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 资源ID
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)  # 操作详情（JSON格式）
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)  # IP地址
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
