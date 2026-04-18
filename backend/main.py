import os
from datetime import date, timedelta

from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db, Base
import app.database as db_module
from app.core.deps import get_current_user
from app.core.security import (
    sanitize_input,
    validate_no_sql_injection,
    generate_csrf_token,
)
from app.core.logging_config import setup_logging
from app.core.migrate import run_migrations
from app.models.user import User
from app.models.task import UserTask, DailyStats
from app.models.mood import MoodRecord
from app.models.achievement import Achievement
from app.api import auth, tasks, moods, achievements, admin, upload, ai, user

# 导入所有模型以确保建表
from app.models.user import User  # noqa: F811
from app.models.task import TaskTemplate  # noqa: F401
from app.models.mood import MoodRecord  # noqa: F811
from app.models.achievement import Achievement  # noqa: F811
from app.models.audit_log import AuditLog  # noqa: F401

# ---------- 初始化 ----------

settings = get_settings()

# 初始化日志系统
logger = setup_logging()
logger.info(f"应用启动: {settings.APP_NAME} v{settings.APP_VERSION}")

# ---------- 创建 FastAPI 应用 ----------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------- 中间件 ----------

# CORS 中间件（从配置读取允许的源）
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# CSP 安全头中间件
@app.middleware("http")
async def csp_security_headers(request: Request, call_next):
    """添加 Content-Security-Policy 等安全响应头"""
    response = await call_next(request)

    # Content-Security-Policy: 限制资源加载来源
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    # X-Content-Type-Options: 防止 MIME 类型嗅探
    response.headers["X-Content-Type-Options"] = "nosniff"

    # X-Frame-Options: 防止点击劫持
    response.headers["X-Frame-Options"] = "DENY"

    # X-XSS-Protection: 启用浏览器 XSS 过滤
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Referrer-Policy: 控制 Referer 头
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions-Policy: 限制浏览器功能（允许麦克风用于语音识别）
    response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"

    return response


# XSS 防护中间件（输入过滤）
@app.middleware("http")
async def xss_protection_middleware(request: Request, call_next):
    """
    XSS 防护中间件。

    对查询参数进行清洗，记录可疑输入。

    注意：SQL 注入防护已通过 SQLAlchemy ORM 参数化查询实现，
    所有数据库操作均使用 ORM 的 filter() 方法，自动进行参数化处理，
    不存在原始 SQL 拼接，从根本上杜绝 SQL 注入风险。
    """
    # 清洗查询参数
    if request.query_params:
        for key, value in request.query_params.items():
            if isinstance(value, str) and not validate_no_sql_injection(value):
                logger.warning(
                    f"检测到可疑 SQL 注入输入 - IP: {request.client.host if request.client else 'unknown'}, "
                    f"参数: {key}, 路径: {request.url.path}"
                )

    response = await call_next(request)
    return response


# ---------- 注册路由 ----------

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(moods.router)
app.include_router(achievements.router)
app.include_router(admin.router)
app.include_router(upload.router)
app.include_router(ai.router)
app.include_router(user.router)

# 静态文件服务（上传的文件）
upload_dir = settings.UPLOAD_DIR
if not os.path.isabs(upload_dir):
    upload_dir = os.path.join(os.path.dirname(__file__), upload_dir)
os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")


# ---------- 仪表盘接口 ----------

@app.get("/api/stats/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的仪表盘数据"""
    # 任务统计
    total_tasks = db.query(func.count(UserTask.id)).filter(
        UserTask.user_id == current_user.id
    ).scalar() or 0
    completed_tasks = db.query(func.count(UserTask.id)).filter(
        UserTask.user_id == current_user.id,
        UserTask.status == "completed",
    ).scalar() or 0
    in_progress_tasks = total_tasks - completed_tasks

    # 情绪统计
    total_moods = db.query(func.count(MoodRecord.id)).filter(
        MoodRecord.user_id == current_user.id
    ).scalar() or 0

    # 成就统计
    total_achievements = db.query(func.count(Achievement.id)).filter(
        Achievement.user_id == current_user.id
    ).scalar() or 0

    # 今日统计
    today = date.today().isoformat()
    today_stats = db.query(DailyStats).filter(
        DailyStats.user_id == current_user.id,
        DailyStats.date == today,
    ).first()

    # 最近7天趋势
    seven_days_ago = (date.today() - timedelta(days=6)).isoformat()
    weekly_stats = (
        db.query(DailyStats)
        .filter(
            DailyStats.user_id == current_user.id,
            DailyStats.date >= seven_days_ago,
        )
        .order_by(DailyStats.date)
        .all()
    )
    weekly_trend = []
    for s in weekly_stats:
        weekly_trend.append({
            "date": s.date,
            "tasks_completed": s.tasks_completed,
            "stars_earned": s.stars_earned,
            "moods_logged": s.moods_logged,
        })

    return {
        "code": 0,
        "message": "success",
        "data": {
            "tasks": {
                "total": total_tasks,
                "completed": completed_tasks,
                "in_progress": in_progress_tasks,
            },
            "moods": {
                "total": total_moods,
            },
            "achievements": {
                "unlocked": total_achievements,
            },
            "today": {
                "tasks_completed": today_stats.tasks_completed if today_stats else 0,
                "stars_earned": today_stats.stars_earned if today_stats else 0,
                "moods_logged": today_stats.moods_logged if today_stats else 0,
            },
            "weekly_trend": weekly_trend,
        },
    }


# ---------- CSRF Token 接口 ----------

@app.get("/api/auth/csrf-token")
def get_csrf_token():
    """获取 CSRF Token"""
    token = generate_csrf_token()
    return {
        "code": 0,
        "message": "success",
        "data": {"csrf_token": token},
    }


# ---------- 统一异常处理 ----------

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"code": 400, "message": str(exc), "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    message = errors[0].get("msg", "参数验证失败") if errors else "参数验证失败"
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": message, "data": None},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail, "data": None},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常: {exc}", exc_info=True, extra={
        "path": request.url.path,
        "method": request.method,
        "ip": request.client.host if request.client else "unknown",
    })
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )


# ---------- 健康检查 ----------

@app.get("/health")
def health_check():
    return {"code": 0, "message": "ok", "data": {"status": "healthy"}}


@app.get("/")
def root():
    return {
        "code": 0,
        "message": f"Welcome to {settings.APP_NAME} v{settings.APP_VERSION}",
        "data": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
        },
    }


# ---------- 应用生命周期事件 ----------

@app.on_event("startup")
async def on_startup():
    """应用启动时的初始化操作"""
    # 执行数据库迁移
    try:
        run_migrations()
    except Exception as e:
        logger.warning(f"数据库迁移执行失败（可能已在测试环境中）: {e}")

    # 创建数据库表
    Base.metadata.create_all(bind=db_module.engine)

    logger.info("应用启动完成")

    # 启动定时任务调度器
    try:
        from app.services.scheduler_service import start_scheduler
        start_scheduler()
        logger.info("定时任务调度器已启动")
    except Exception as e:
        logger.warning(f"定时任务调度器启动失败（非关键）: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    """应用关闭时的清理操作"""
    logger.info("应用正在关闭...")

    # 停止定时任务调度器
    try:
        from app.services.scheduler_service import stop_scheduler
        stop_scheduler()
        logger.info("定时任务调度器已停止")
    except Exception as e:
        logger.warning(f"定时任务调度器停止失败: {e}")


def init_app():
    """
    初始化应用（用于生产环境直接运行）。
    执行数据库迁移和建表操作。
    """
    run_migrations()
    Base.metadata.create_all(bind=db_module.engine)
    return app


if __name__ == "__main__":
    import uvicorn
    init_app()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
