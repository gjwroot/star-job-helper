import json
from datetime import date

from sqlalchemy.orm import Session

from app.models.mood import MoodRecord
from app.models.task import DailyStats


# 情绪对应的建议
MOOD_TIPS = {
    "happy": [
        "继续保持好心情！",
        "把快乐分享给身边的人吧！",
        "记录下让你开心的事情，以后回味。",
    ],
    "calm": [
        "平静是一种力量，好好享受。",
        "适合做一些需要专注的事情。",
        "深呼吸，感受当下的宁静。",
    ],
    "anxious": [
        "试着深呼吸：吸气4秒，屏住4秒，呼气4秒。",
        "把焦虑的事情写下来，逐个分析。",
        "和信任的人聊聊你的感受。",
        "做一些简单的运动来放松。",
    ],
    "sad": [
        "允许自己难过，这是正常的情绪。",
        "试着做一些让自己开心的小事。",
        "听听喜欢的音乐，或者出去走走。",
        "如果持续低落，建议寻求专业帮助。",
    ],
    "angry": [
        "先离开让你生气的地方，冷静一下。",
        "数到10再做决定。",
        "运动是释放愤怒的好方法。",
        "等冷静后再沟通，效果会更好。",
    ],
}


class MoodService:
    """情绪服务"""

    @staticmethod
    def record_mood(db: Session, user_id: int, mood_type: str) -> MoodRecord:
        """记录情绪"""
        if mood_type not in MOOD_TIPS:
            raise ValueError(f"不支持的情绪类型: {mood_type}，支持: {', '.join(MOOD_TIPS.keys())}")

        tips = MOOD_TIPS.get(mood_type, [])
        record = MoodRecord(
            user_id=user_id,
            mood_type=mood_type,
            tips=json.dumps(tips, ensure_ascii=False),
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        # 更新每日统计
        today = date.today().isoformat()
        stats = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date == today,
        ).first()
        if stats is None:
            stats = DailyStats(user_id=user_id, date=today)
            db.add(stats)
            db.flush()
        stats.moods_logged = (stats.moods_logged or 0) + 1
        db.commit()

        return record

    @staticmethod
    def get_history(db: Session, user_id: int, limit: int = 30) -> list[MoodRecord]:
        """获取情绪历史"""
        return (
            db.query(MoodRecord)
            .filter(MoodRecord.user_id == user_id)
            .order_by(MoodRecord.created_at.desc())
            .limit(limit)
            .all()
        )
