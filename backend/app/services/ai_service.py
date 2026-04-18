"""
AI 服务层 - 使用规则引擎模拟 AI 能力（不依赖外部 API）
后续可替换为真实 AI API（如 OpenAI、文心一言等）
"""

import random
from datetime import date, timedelta

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.models.task import UserTask, DailyStats
from app.models.mood import MoodRecord


class AIService:
    """AI 服务 - 基于规则引擎的智能辅助"""

    # ========== 沟通语句生成 ==========

    COMM_TEMPLATES = {
        "greeting": [
            "大家好，我是{name}，请多关照！",
            "你好！很高兴认识你，我是{name}。",
            "早上好！今天天气真不错呢。",
            "大家好，希望和大家成为好朋友！",
        ],
        "workplace": [
            "请问这个文件应该放在哪里？",
            "我不太确定这个任务怎么做，能帮我看一下吗？",
            "谢谢你的帮助，我学会了！",
            "我需要休息一下，可以吗？",
            "请问洗手间在哪里？",
        ],
        "emotion_positive": [
            "我今天很开心！",
            "这个工作让我很有成就感！",
            "谢谢大家对我的帮助！",
            "我觉得自己进步了很多！",
        ],
        "emotion_negative": [
            "我现在有点紧张，能陪我一下吗？",
            "我今天心情不太好，想一个人待一会儿。",
            "我感到有些焦虑，可以休息一下吗？",
            "这个任务对我来说有点难，能再教我一次吗？",
        ],
        "request": [
            "可以帮我看一下这个吗？",
            "能陪我一起做这个任务吗？",
            "我需要多一点时间，可以吗？",
            "我不太明白，能再说一遍吗？",
        ],
    }

    # ========== 聊天陪伴规则 ==========

    CHAT_RULES = [
        {
            "keywords": ["紧张", "害怕", "担心", "不安", "恐惧"],
            "replies": [
                "深呼吸，慢慢来。紧张是很正常的反应，你做得已经很好了！要不要试试深呼吸放松一下？",
                "没关系，每个人都会紧张。你愿意告诉我是什么让你紧张吗？我们一起想办法。",
                "紧张说明你在乎这件事，这很好。试试把手放在胸口，感受心跳，慢慢呼吸。",
            ],
        },
        {
            "keywords": ["开心", "高兴", "棒", "太好了", "哈哈", "嘻嘻"],
            "replies": [
                "太好了！你的开心让我也很高兴！继续保持好心情，今天一定会很棒的！",
                "看到你开心我也好开心！是什么好事呢？跟我分享一下呗！",
                "开心的你最有魅力了！把这份快乐传递给身边的人吧！",
            ],
        },
        {
            "keywords": ["累", "tired", "困", "疲惫", "好累", "好困"],
            "replies": [
                "辛苦了！累了就休息一下吧。休息是为了更好地出发，你已经很努力了！",
                "身体是革命的本钱，累了记得喝水、伸展一下。你已经做得很好了！",
                "累了是正常的，说明你今天很认真。去休息一下吧，回来再继续加油！",
            ],
        },
        {
            "keywords": ["笑话", "开心", "funny", "搞笑", "逗我"],
            "replies": [
                "为什么程序员总是分不清万圣节和圣诞节？因为 Oct 31 = Dec 25（八进制的31等于十进制的25）",
                "有一天，小明问爸爸：爸爸，为什么别人都说我们家的人没有脑子？爸爸说：你过来，我给你讲讲。",
                "老师问小明：你长大想做什么？小明说：我想做一个有钱人。老师说：那你要好好学习。小明说：不，我想做一个有钱人的孩子。",
                "为什么数学书总是不开心？因为它有太多问题了！",
            ],
        },
        {
            "keywords": ["谢谢", "感谢", "多谢", "thanks"],
            "replies": [
                "不客气！能帮到你我很开心。如果还有什么需要，随时告诉我哦！",
                "不用谢！你随时都可以找我聊天。希望你今天一切顺利！",
                "能帮到你是我最开心的事！加油，你一定可以的！",
            ],
        },
        {
            "keywords": ["工作", "任务", "上班", "干活"],
            "replies": [
                "今天的工作进展怎么样？如果遇到困难，可以试试把任务分成更小的步骤来完成。一步一步来，你可以的！",
                "工作加油！记得适时休息，效率会更高哦。有什么需要帮忙的随时说！",
                "你对待工作的态度真的很棒！遇到不会的不要怕，大胆去问就好。",
            ],
        },
        {
            "keywords": ["生气", "愤怒", "烦", "讨厌", "气死"],
            "replies": [
                "我理解你的感受。生气的时候先深呼吸，数到10，让自己冷静一下。你愿意说说发生了什么吗？",
                "生气是正常的情绪，不要压抑自己。不过先冷静下来，再做决定会更好。",
                "我能感受到你现在很不开心。要不要先离开那个环境，去喝杯水或者散散步？",
            ],
        },
        {
            "keywords": ["难过", "伤心", "哭", "悲伤", "不开心"],
            "replies": [
                "难过的时候，允许自己哭出来，这是正常的。我在这里陪着你。",
                "每个人都会有难过的时候，这不代表你不好。明天又是新的一天，一切都会好起来的。",
                "你的感受很重要。如果愿意的话，可以跟我说说是什么让你难过。",
            ],
        },
        {
            "keywords": ["你好", "在吗", "嗨", "hi", "hello"],
            "replies": [
                "你好呀！很高兴见到你！今天过得怎么样？",
                "嗨！我在呢！有什么想聊的吗？",
                "你好！今天心情怎么样？跟我说说吧！",
            ],
        },
        {
            "keywords": ["再见", "拜拜", "bye", "下次见"],
            "replies": [
                "再见！祝你今天一切顺利！下次再来找我聊天哦！",
                "拜拜！记得按时休息，照顾好自己！",
                "下次见！有什么需要随时来找我！",
            ],
        },
        {
            "keywords": ["无聊", "没意思", "好闲"],
            "replies": [
                "无聊的时候可以试试做一个小任务，完成后会有成就感哦！要不要去看看任务列表？",
                "无聊也是一种休息。不如听听音乐、散散步，或者跟我聊聊天？",
                "可以试试记录一下今天的心情，或者看看有没有什么新的成就可以解锁！",
            ],
        },
        {
            "keywords": ["睡不着", "失眠", "不想睡"],
            "replies": [
                "睡不着的时候可以试试：闭上眼睛，慢慢呼吸，想象一个让你放松的地方。不要给自己压力。",
                "睡前可以试试听一些轻柔的音乐，或者做几次深呼吸。不要看手机哦！",
                "如果实在睡不着，不要焦虑，起来喝杯温水，等有困意了再回去睡。",
            ],
        },
    ]

    DEFAULT_REPLIES = [
        "我在呢！有什么想聊的吗？你可以告诉我你今天的心情，或者工作中遇到的事情。",
        "嗯嗯，我在听。你继续说，我陪你。",
        "有什么我可以帮你的吗？不管是工作上的还是心情上的，都可以跟我说。",
        "谢谢你跟我聊天！你今天有什么特别的事情想分享吗？",
        "我随时都在这里陪你。累了就休息，开心了就笑，难过了我安慰你。",
    ]

    # ========== 鼓励语 ==========

    ENCOURAGEMENTS = [
        "你今天做得很棒！继续保持！",
        "每一天的努力都在让你变得更好！",
        "你已经比昨天进步了，真了不起！",
        "相信自己的能力，你比想象中更强大！",
        "坚持就是胜利，你做得非常好！",
        "你的努力大家都看在眼里，继续加油！",
        "不管结果如何，你勇于尝试就已经很棒了！",
        "每完成一个小目标，你就离大目标更近了一步！",
    ]

    @classmethod
    def generate_comm_speech(cls, scene: str, context: str, user_name: str = "我") -> str:
        """
        根据场景生成沟通语句。

        Args:
            scene: 场景类型 (greeting, workplace, emotion_positive, emotion_negative, request)
            context: 上下文信息
            user_name: 用户名字

        Returns:
            生成的沟通语句
        """
        # 确定场景类别
        category = "greeting"  # 默认
        if any(kw in context for kw in ["工作", "任务", "文件", "办公室"]):
            category = "workplace"
        elif any(kw in context for kw in ["开心", "高兴", "棒", "成就感"]):
            category = "emotion_positive"
        elif any(kw in context for kw in ["紧张", "害怕", "难过", "焦虑"]):
            category = "emotion_negative"
        elif any(kw in context for kw in ["帮助", "请教", "陪", "一起"]):
            category = "request"

        # 如果明确指定了场景，优先使用
        if scene in cls.COMM_TEMPLATES:
            category = scene

        templates = cls.COMM_TEMPLATES.get(category, cls.COMM_TEMPLATES["greeting"])
        return random.choice(templates).format(name=user_name)

    @classmethod
    def generate_daily_summary(cls, user_id: int, db: Session) -> dict:
        """
        生成每日工作总结。

        Args:
            user_id: 用户 ID
            db: 数据库会话

        Returns:
            结构化的每日总结
        """
        today = date.today().isoformat()

        # 今日任务完成数
        tasks_completed = db.query(func.count(UserTask.id)).filter(
            and_(
                UserTask.user_id == user_id,
                UserTask.status == "completed",
                func.date(UserTask.completed_at) == today,
            )
        ).scalar() or 0

        # 今日总任务数
        total_tasks = db.query(func.count(UserTask.id)).filter(
            and_(
                UserTask.user_id == user_id,
                func.date(UserTask.created_at) == today,
            )
        ).scalar() or 0

        # 今日星星数
        today_stats = db.query(DailyStats).filter(
            and_(
                DailyStats.user_id == user_id,
                DailyStats.date == today,
            )
        ).first()
        stars_earned = today_stats.stars_earned if today_stats else 0

        # 今日情绪记录
        today_moods = db.query(MoodRecord).filter(
            and_(
                MoodRecord.user_id == user_id,
                func.date(MoodRecord.created_at) == today,
            )
        ).all()

        # 情绪分析
        mood_counts = {}
        mood_labels = {
            "happy": "开心",
            "calm": "平静",
            "anxious": "焦虑",
            "sad": "难过",
            "angry": "生气",
            "tired": "疲惫",
        }
        for mood in today_moods:
            mood_counts[mood.mood_type] = mood_counts.get(mood.mood_type, 0) + 1

        # 主要情绪
        main_mood = "平静"
        main_mood_emoji = "😌"
        mood_emoji_map = {
            "happy": "😄", "calm": "😌", "anxious": "😰",
            "sad": "😢", "angry": "😤", "tired": "😴",
        }
        if mood_counts:
            main_mood = max(mood_counts, key=mood_counts.get)
            main_mood = mood_labels.get(main_mood, main_mood)
            main_mood_emoji = mood_emoji_map.get(main_mood, "😊")

        # 情绪变化描述
        mood_change_desc = ""
        if len(today_moods) >= 2:
            first_mood = today_moods[0].mood_type
            last_mood = today_moods[-1].mood_type
            if first_mood != last_mood:
                mood_change_desc = (
                    f"今天的情绪从{mood_labels.get(first_mood, first_mood)}变为了"
                    f"{mood_labels.get(last_mood, last_mood)}"
                )
            else:
                mood_change_desc = f"今天的情绪一直比较{mood_labels.get(first_mood, first_mood)}"
        elif len(today_moods) == 1:
            mood_change_desc = f"今天记录了一次{mood_labels.get(today_moods[0].mood_type, today_moods[0].mood_type)}的心情"
        else:
            mood_change_desc = "今天还没有记录心情哦，记得记录一下"

        # 生成鼓励语
        encouragement = random.choice(cls.ENCOURAGEMENTS)
        if tasks_completed > 0:
            encouragement = f"今天完成了{tasks_completed}个任务，{encouragement}"
        elif total_tasks > 0:
            encouragement = f"今天开始了{total_tasks}个任务，虽然还没完成，但{encouragement}"

        return {
            "date": today,
            "tasks_completed": tasks_completed,
            "total_tasks": total_tasks,
            "stars_earned": stars_earned,
            "moods_logged": len(today_moods),
            "main_mood": main_mood,
            "main_mood_emoji": main_mood_emoji,
            "mood_counts": mood_counts,
            "mood_change_desc": mood_change_desc,
            "encouragement": encouragement,
        }

    @classmethod
    def adaptive_difficulty(cls, user_id: int, db: Session) -> dict:
        """
        根据完成情况调整任务难度建议。

        Args:
            user_id: 用户 ID
            db: 数据库会话

        Returns:
            难度建议
        """
        seven_days_ago = (date.today() - timedelta(days=7)).isoformat()

        # 最近7天完成的任务数
        completed_count = db.query(func.count(UserTask.id)).filter(
            and_(
                UserTask.user_id == user_id,
                UserTask.status == "completed",
                func.date(UserTask.completed_at) >= seven_days_ago,
            )
        ).scalar() or 0

        # 最近7天创建的总任务数
        total_count = db.query(func.count(UserTask.id)).filter(
            and_(
                UserTask.user_id == user_id,
                func.date(UserTask.created_at) >= seven_days_ago,
            )
        ).scalar() or 0

        # 完成率
        completion_rate = (completed_count / total_count * 100) if total_count > 0 else 0

        # 最近7天情绪统计
        recent_moods = db.query(MoodRecord).filter(
            and_(
                MoodRecord.user_id == user_id,
                func.date(MoodRecord.created_at) >= seven_days_ago,
            )
        ).all()

        # 计算平均情绪值
        mood_value_map = {"happy": 5, "calm": 4, "anxious": 2, "sad": 2, "angry": 1, "tired": 0}
        if recent_moods:
            avg_mood = sum(mood_value_map.get(m.mood_type, 3) for m in recent_moods) / len(recent_moods)
        else:
            avg_mood = 3

        # 难度建议
        if completion_rate >= 80 and avg_mood >= 3.5:
            difficulty = "increase"
            difficulty_label = "提升难度"
            suggestion = (
                "你最近表现非常出色！任务完成率很高，心情也不错。"
                "可以尝试挑战一些更有难度的任务，比如需要更多步骤的任务。"
            )
        elif completion_rate >= 60:
            difficulty = "maintain"
            difficulty_label = "保持当前"
            suggestion = (
                "你最近的表现很稳定！继续保持这个节奏就好。"
                "如果觉得太简单了，可以适当增加难度；如果觉得吃力，也不要着急。"
            )
        elif completion_rate >= 30:
            difficulty = "slight_decrease"
            difficulty_label = "适当降低"
            suggestion = (
                "你最近有些任务还没完成，没关系。可以试试把任务分成更小的步骤，"
                "一步一步来完成。慢慢来，不着急。"
            )
        else:
            difficulty = "decrease"
            difficulty_label = "降低难度"
            suggestion = (
                "最近的任务完成得不多，可能需要一些更简单的任务来建立信心。"
                "建议从步骤少的任务开始，完成后会更有动力！"
            )

        return {
            "period": "最近7天",
            "completed_tasks": completed_count,
            "total_tasks": total_count,
            "completion_rate": round(completion_rate, 1),
            "avg_mood_score": round(avg_mood, 1),
            "mood_records": len(recent_moods),
            "difficulty": difficulty,
            "difficulty_label": difficulty_label,
            "suggestion": suggestion,
        }

    @classmethod
    def chat_companion(cls, message: str, mood_history: list = None) -> str:
        """
        AI 聊天陪伴 - 基于关键词匹配 + 情绪上下文的规则引擎。

        Args:
            message: 用户消息
            mood_history: 最近情绪记录列表，如 ["happy", "calm", "anxious"]

        Returns:
            AI 回复
        """
        message_lower = message.lower().strip()

        # 如果消息为空
        if not message_lower:
            return "你好像没有说什么，想聊什么呢？"

        # 关键词匹配
        best_match = None
        best_match_count = 0

        for rule in cls.CHAT_RULES:
            match_count = sum(1 for kw in rule["keywords"] if kw.lower() in message_lower)
            if match_count > best_match_count:
                best_match_count = match_count
                best_match = rule

        if best_match and best_match_count > 0:
            reply = random.choice(best_match["replies"])
        else:
            reply = random.choice(cls.DEFAULT_REPLIES)

        # 根据情绪上下文调整回复
        if mood_history and len(mood_history) > 0:
            recent_mood = mood_history[-1]
            if recent_mood in ["sad", "angry", "anxious"]:
                # 如果最近情绪不好，增加温暖感
                warm_suffixes = [
                    " 记住，不管发生什么，我都在这里陪你。",
                    " 你不是一个人，有困难随时跟我说。",
                    " 照顾好自己，你已经很棒了。",
                ]
                if random.random() < 0.5:  # 50% 概率追加温暖语
                    reply += random.choice(warm_suffixes)

        return reply
