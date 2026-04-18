from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaskTemplate(Base):
    """任务模板"""

    __tablename__ = "task_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    steps: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 字符串
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    creator = relationship("User", back_populates="created_templates")
    user_tasks = relationship("UserTask", back_populates="template", lazy="selectin")


class UserTask(Base):
    """用户任务"""

    __tablename__ = "user_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("task_templates.id"), nullable=False)
    completed_steps: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 字符串，已完成步骤索引列表
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)  # in_progress / completed
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    user = relationship("User", back_populates="tasks")
    template = relationship("TaskTemplate", back_populates="user_tasks")


class DailyStats(Base):
    """每日统计"""

    __tablename__ = "daily_stats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stars_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    moods_logged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 关系
    user = relationship("User", back_populates="daily_stats")
