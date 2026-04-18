"""
AI 相关 API 路由
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/ai", tags=["AI"])


# ---------- 请求模型 ----------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="用户消息")
    mood_history: list[str] = Field(default=[], description="最近情绪记录列表")


class CommSpeechRequest(BaseModel):
    scene: str = Field(default="", description="场景类型")
    context: str = Field(..., min_length=1, max_length=200, description="上下文信息")


# ---------- 接口 ----------

@router.post("/chat")
def ai_chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 聊天陪伴"""
    reply = AIService.chat_companion(req.message, req.mood_history)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "reply": reply,
        },
    }


@router.post("/comm-speech")
def generate_comm_speech(
    req: CommSpeechRequest,
    current_user: User = Depends(get_current_user),
):
    """生成沟通语句"""
    speech = AIService.generate_comm_speech(req.scene, req.context, current_user.name)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "speech": speech,
        },
    }


@router.get("/daily-summary")
def get_daily_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取每日总结"""
    summary = AIService.generate_daily_summary(current_user.id, db)
    return {
        "code": 0,
        "message": "success",
        "data": summary,
    }


@router.get("/difficulty-suggestion")
def get_difficulty_suggestion(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取难度建议"""
    suggestion = AIService.adaptive_difficulty(current_user.id, db)
    return {
        "code": 0,
        "message": "success",
        "data": suggestion,
    }
