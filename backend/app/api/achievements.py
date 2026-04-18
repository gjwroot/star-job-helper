from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.achievement_service import AchievementService

router = APIRouter(prefix="/api/achievements", tags=["成就"])


@router.get("")
def get_achievements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取我的成就"""
    unlocked = AchievementService.get_user_achievements(db, current_user.id)
    definitions = AchievementService.get_all_definitions()

    unlocked_ids = {a.achievement_id for a in unlocked}
    result = []
    for ach_id, ach_def in definitions.items():
        result.append({
            "achievement_id": ach_id,
            "name": ach_def["name"],
            "description": ach_def["description"],
            "icon": ach_def["icon"],
            "unlocked": ach_id in unlocked_ids,
        })

    return {
        "code": 0,
        "message": "success",
        "data": {
            "achievements": result,
            "unlocked_count": len(unlocked),
            "total_count": len(definitions),
        },
    }
