from sqlalchemy.orm import Session

from app.models.achievement import Achievement


# 成就定义
ACHIEVEMENT_DEFINITIONS = {
    "first_task": {"name": "初出茅庐", "description": "完成第一个任务", "icon": "star"},
    "five_tasks": {"name": "勤勉之星", "description": "累计完成5个任务", "icon": "fire"},
    "ten_tasks": {"name": "任务达人", "description": "累计完成10个任务", "icon": "trophy"},
    "first_mood": {"name": "情绪观察者", "description": "记录第一次情绪", "icon": "heart"},
    "week_streak": {"name": "坚持一周", "description": "连续7天有活动记录", "icon": "calendar"},
}


class AchievementService:
    """成就服务"""

    @staticmethod
    def get_user_achievements(db: Session, user_id: int) -> list[Achievement]:
        """获取用户的成就列表"""
        return (
            db.query(Achievement)
            .filter(Achievement.user_id == user_id)
            .order_by(Achievement.unlocked_at.desc())
            .all()
        )

    @staticmethod
    def get_all_definitions() -> dict:
        """获取所有成就定义"""
        return ACHIEVEMENT_DEFINITIONS

    @staticmethod
    def unlock_achievement(db: Session, user_id: int, achievement_id: str) -> Achievement | None:
        """解锁成就（如果尚未解锁）"""
        if achievement_id not in ACHIEVEMENT_DEFINITIONS:
            raise ValueError(f"未知的成就: {achievement_id}")

        existing = db.query(Achievement).filter(
            Achievement.user_id == user_id,
            Achievement.achievement_id == achievement_id,
        ).first()
        if existing:
            return None  # 已解锁

        achievement = Achievement(user_id=user_id, achievement_id=achievement_id)
        db.add(achievement)
        db.commit()
        db.refresh(achievement)
        return achievement
