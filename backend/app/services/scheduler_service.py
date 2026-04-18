"""
定时任务服务。

使用 APScheduler 实现定时任务调度：
- 每日 22:00 自动生成日报摘要
- 每小时检查是否有需要提醒的用户

使用方式:
    from app.services.scheduler_service import start_scheduler

    # 在应用启动时调用
    start_scheduler()
"""

import logging
from datetime import date, datetime, timedelta

logger = logging.getLogger("star_job_helper.scheduler")

# 调度器实例
_scheduler = None


def _generate_daily_summary():
    """
    每日 22:00 执行：生成日报摘要。

    遍历所有活跃用户，生成当日任务完成情况、情绪记录等摘要。
    """
    logger.info("开始生成每日日报摘要...")

    try:
        from app.database import SessionLocal
        from app.models.user import User
        from app.models.task import UserTask, DailyStats
        from app.models.mood import MoodRecord
        from sqlalchemy import func

        db = SessionLocal()
        try:
            today = date.today().isoformat()

            # 获取今日有活动的用户
            active_users = db.query(User).join(DailyStats).filter(
                DailyStats.date == today
            ).all()

            summary_count = 0
            for user in active_users:
                stats = db.query(DailyStats).filter(
                    DailyStats.user_id == user.id,
                    DailyStats.date == today,
                ).first()

                if stats:
                    summary_count += 1
                    logger.info(
                        f"用户 {user.name}(ID:{user.id}) 日报: "
                        f"完成任务 {stats.tasks_completed} 个, "
                        f"获得星星 {stats.stars_earned} 个, "
                        f"记录情绪 {stats.moods_logged} 次"
                    )

            logger.info(f"日报摘要生成完成，共 {summary_count} 位活跃用户")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"生成日报摘要失败: {e}", exc_info=True)


def _check_reminders():
    """
    每小时执行：检查需要提醒的用户。

    检查逻辑：
    - 今日尚未记录情绪的用户
    - 今日有未完成任务的用户
    """
    logger.info("开始检查用户提醒...")

    try:
        from app.database import SessionLocal
        from app.models.user import User
        from app.models.task import UserTask, DailyStats
        from app.models.mood import MoodRecord
        from sqlalchemy import and_, not_

        db = SessionLocal()
        try:
            today = date.today().isoformat()

            # 查找今日有未完成任务的用户
            users_with_pending = (
                db.query(User)
                .join(UserTask, UserTask.user_id == User.id)
                .filter(
                    UserTask.status == "in_progress",
                )
                .distinct()
                .all()
            )

            # 查找今日未记录情绪的用户（排除今天已记录的）
            users_with_moods_today = (
                db.query(MoodRecord.user_id)
                .filter(MoodRecord.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0))
                .distinct()
                .subquery()
            )

            all_users = db.query(User).all()
            users_without_mood = [
                u for u in all_users
                if u.id not in [r[0] for r in db.query(users_with_moods_today.c.user_id).all()]
            ]

            logger.info(
                f"提醒检查完成: "
                f"{len(users_with_pending)} 位用户有未完成任务, "
                f"{len(users_without_mood)} 位用户今日未记录情绪"
            )

            # TODO: 在实际应用中，这里可以集成推送通知服务
            # 例如：发送微信消息、短信、邮件等

        finally:
            db.close()

    except Exception as e:
        logger.error(f"检查用户提醒失败: {e}", exc_info=True)


def start_scheduler():
    """
    启动定时任务调度器。

    优先使用 APScheduler，如果不可用则回退到 threading.Timer。
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("调度器已在运行中")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger

        _scheduler = BackgroundScheduler()

        # 每日 22:00 生成日报摘要
        _scheduler.add_job(
            _generate_daily_summary,
            trigger=CronTrigger(hour=22, minute=0),
            id="daily_summary",
            name="每日日报摘要",
            replace_existing=True,
        )

        # 每小时检查用户提醒
        _scheduler.add_job(
            _check_reminders,
            trigger=IntervalTrigger(hours=1),
            id="check_reminders",
            name="用户提醒检查",
            replace_existing=True,
        )

        _scheduler.start()
        logger.info("APScheduler 调度器启动成功")

    except ImportError:
        logger.warning("APScheduler 未安装，使用 threading.Timer 作为替代")
        _start_fallback_scheduler()


def _start_fallback_scheduler():
    """
    使用 threading.Timer 实现简单的定时任务。

    注意：这不是生产级方案，仅作为 APScheduler 不可用时的降级方案。
    """
    import threading

    def _schedule_daily():
        """每日任务（简化版：每小时检查一次是否到了 22:00）"""
        now = datetime.now()
        if now.hour == 22 and now.minute < 1:
            _generate_daily_summary()
        _check_reminders()

        # 1 小时后再次执行
        timer = threading.Timer(3600, _schedule_daily)
        timer.daemon = True
        timer.start()

    # 启动
    timer = threading.Timer(60, _schedule_daily)  # 1 分钟后首次执行
    timer.daemon = True
    timer.start()

    logger.info("threading.Timer 降级调度器启动成功")


def stop_scheduler():
    """停止定时任务调度器"""
    global _scheduler

    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("调度器已停止")
        except Exception as e:
            logger.error(f"停止调度器失败: {e}")
        finally:
            _scheduler = None


def get_scheduler_status() -> dict:
    """获取调度器状态"""
    global _scheduler

    if _scheduler is None:
        return {"status": "not_running", "type": "none"}

    try:
        jobs = _scheduler.get_jobs()
        return {
            "status": "running",
            "type": "apscheduler",
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": str(job.next_run_time) if job.next_run_time else None,
                }
                for job in jobs
            ],
        }
    except Exception:
        return {"status": "running", "type": "threading_timer"}
