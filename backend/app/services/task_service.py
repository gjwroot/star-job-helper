import json
from datetime import datetime, date

from sqlalchemy.orm import Session

from app.models.task import TaskTemplate, UserTask, DailyStats
from app.models.achievement import Achievement


class TaskService:
    """任务服务"""

    @staticmethod
    def get_templates(db: Session, is_public: bool = True) -> list[TaskTemplate]:
        """获取任务模板列表"""
        query = db.query(TaskTemplate)
        if is_public:
            query = query.filter(TaskTemplate.is_public == True)  # noqa: E712
        return query.order_by(TaskTemplate.created_at.desc()).all()

    @staticmethod
    def create_template(
        db: Session,
        name: str,
        steps: list[str],
        icon: str | None,
        created_by: int,
        is_public: bool = True,
    ) -> TaskTemplate:
        """创建任务模板"""
        template = TaskTemplate(
            name=name,
            icon=icon,
            steps=json.dumps(steps, ensure_ascii=False),
            created_by=created_by,
            is_public=is_public,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def get_my_tasks(db: Session, user_id: int) -> list[UserTask]:
        """获取用户的任务列表"""
        return (
            db.query(UserTask)
            .filter(UserTask.user_id == user_id)
            .order_by(UserTask.created_at.desc())
            .all()
        )

    @staticmethod
    def create_user_task(db: Session, user_id: int, template_id: int) -> UserTask:
        """为用户创建一个任务"""
        template = db.query(TaskTemplate).filter(TaskTemplate.id == template_id).first()
        if template is None:
            raise ValueError("任务模板不存在")

        user_task = UserTask(
            user_id=user_id,
            template_id=template_id,
            completed_steps=json.dumps([]),
            status="in_progress",
        )
        db.add(user_task)
        db.commit()
        db.refresh(user_task)
        return user_task

    @staticmethod
    def toggle_step(db: Session, user_id: int, task_id: int, step_index: int) -> UserTask:
        """完成或取消某个步骤"""
        user_task = db.query(UserTask).filter(
            UserTask.id == task_id,
            UserTask.user_id == user_id,
        ).first()
        if user_task is None:
            raise ValueError("任务不存在")

        completed_steps = json.loads(user_task.completed_steps) if user_task.completed_steps else []

        if step_index in completed_steps:
            completed_steps.remove(step_index)
        else:
            completed_steps.append(step_index)

        user_task.completed_steps = json.dumps(completed_steps)

        # 检查是否所有步骤都完成了
        template = db.query(TaskTemplate).filter(TaskTemplate.id == user_task.template_id).first()
        if template and template.steps:
            total_steps = len(json.loads(template.steps))
            if len(completed_steps) >= total_steps:
                user_task.status = "completed"
                user_task.completed_at = datetime.utcnow()
                # 更新每日统计
                TaskService._update_daily_stats(db, user_id, "tasks_completed")
                TaskService._update_daily_stats(db, user_id, "stars_earned")
                # 检查成就
                TaskService._check_achievements(db, user_id)

        db.commit()
        db.refresh(user_task)
        return user_task

    @staticmethod
    def _update_daily_stats(db: Session, user_id: int, field: str):
        """更新每日统计"""
        today = date.today().isoformat()
        stats = db.query(DailyStats).filter(
            DailyStats.user_id == user_id,
            DailyStats.date == today,
        ).first()
        if stats is None:
            stats = DailyStats(user_id=user_id, date=today)
            db.add(stats)
            db.flush()
        setattr(stats, field, (getattr(stats, field) or 0) + 1)

    @staticmethod
    def _check_achievements(db: Session, user_id: int):
        """检查并解锁成就"""
        completed_count = (
            db.query(UserTask)
            .filter(UserTask.user_id == user_id, UserTask.status == "completed")
            .count()
        )

        achievement_map = {
            "first_task": 1,
            "five_tasks": 5,
            "ten_tasks": 10,
        }

        for ach_id, threshold in achievement_map.items():
            if completed_count >= threshold:
                existing = db.query(Achievement).filter(
                    Achievement.user_id == user_id,
                    Achievement.achievement_id == ach_id,
                ).first()
                if existing is None:
                    achievement = Achievement(user_id=user_id, achievement_id=ach_id)
                    db.add(achievement)
