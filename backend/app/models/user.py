from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """用户模型"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)  # user / counselor / admin
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    tasks = relationship("UserTask", back_populates="user", lazy="selectin")
    mood_records = relationship("MoodRecord", back_populates="user", lazy="selectin")
    achievements = relationship("Achievement", back_populates="user", lazy="selectin")
    daily_stats = relationship("DailyStats", back_populates="user", lazy="selectin")
    created_templates = relationship("TaskTemplate", back_populates="creator", lazy="selectin")
