from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MoodRecord(Base):
    """情绪记录"""

    __tablename__ = "mood_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    mood_type: Mapped[str] = mapped_column(String(20), nullable=False)  # happy / calm / anxious / sad / angry
    tips: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 字符串，建议列表
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    user = relationship("User", back_populates="mood_records")
