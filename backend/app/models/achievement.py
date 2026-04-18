from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Achievement(Base):
    """成就记录"""

    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id: Mapped[str] = mapped_column(String(50), nullable=False)  # 成就标识符
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    user = relationship("User", back_populates="achievements")
