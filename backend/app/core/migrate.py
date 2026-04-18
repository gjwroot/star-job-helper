"""
数据库版本管理和迁移模块。

使用简单的版本号记录在 settings 表中，支持自动执行迁移脚本。

使用方式:
    from app.core.migrate import run_migrations

    # 在应用启动时调用
    run_migrations(db_engine)
"""

import logging
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, text, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger("star_job_helper.migrate")

settings = get_settings()

# ---------- 迁移版本定义 ----------
# 每个迁移是一个函数，接收 Session 对象
# key: 版本号, value: (描述, 迁移函数)
MIGRATIONS: dict[int, tuple[str, object]] = {}


def migration(version: int, description: str):
    """迁移注册装饰器"""
    def decorator(func):
        MIGRATIONS[version] = (description, func)
        return func
    return decorator


# ---------- 迁移脚本 ----------

@migration(1, "创建 settings 表用于版本管理")
def _migrate_001_create_settings_table(db: Session):
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL UNIQUE,
            description TEXT,
            applied_at TEXT NOT NULL
        )
    """))
    db.commit()


@migration(2, "为 users 表添加 email 字段")
def _migrate_002_add_user_email(db: Session):
    # 检查字段是否已存在
    result = db.execute(text("PRAGMA table_info(users)"))
    columns = [row[1] for row in result.fetchall()]
    if "email" not in columns:
        db.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(100)"))
        db.commit()
        logger.info("迁移 002: 为 users 表添加 email 字段")


@migration(3, "为 users 表添加 is_active 字段")
def _migrate_003_add_user_is_active(db: Session):
    result = db.execute(text("PRAGMA table_info(users)"))
    columns = [row[1] for row in result.fetchall()]
    if "is_active" not in columns:
        db.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
        db.commit()
        logger.info("迁移 003: 为 users 表添加 is_active 字段")


@migration(4, "为 mood_records 表添加 note 字段")
def _migrate_004_add_mood_note(db: Session):
    result = db.execute(text("PRAGMA table_info(mood_records)"))
    columns = [row[1] for row in result.fetchall()]
    if "note" not in columns:
        db.execute(text("ALTER TABLE mood_records ADD COLUMN note TEXT"))
        db.commit()
        logger.info("迁移 004: 为 mood_records 表添加 note 字段")


@migration(5, "为 user_tasks 表添加 stars 字段")
def _migrate_005_add_task_stars(db: Session):
    result = db.execute(text("PRAGMA table_info(user_tasks)"))
    columns = [row[1] for row in result.fetchall()]
    if "stars" not in columns:
        db.execute(text("ALTER TABLE user_tasks ADD COLUMN stars INTEGER DEFAULT 0"))
        db.commit()
        logger.info("迁移 005: 为 user_tasks 表添加 stars 字段")


# ---------- 迁移执行引擎 ----------

def _get_current_version(db: Session) -> int:
    """获取当前数据库版本号"""
    try:
        result = db.execute(text("SELECT MAX(version) FROM _migrations"))
        row = result.fetchone()
        return row[0] if row and row[0] else 0
    except Exception:
        return 0


def _record_migration(db: Session, version: int, description: str):
    """记录已执行的迁移"""
    db.execute(text(
        "INSERT INTO _migrations (version, description, applied_at) VALUES (:v, :d, :t)"
    ), {"v": version, "d": description, "t": datetime.utcnow().isoformat()})
    db.commit()


def run_migrations(engine=None):
    """
    执行所有待运行的数据库迁移。

    Args:
        engine: SQLAlchemy 引擎，默认使用 app.database.engine
    """
    if engine is None:
        from app.database import engine as default_engine
        engine = default_engine

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        current_version = _get_current_version(db)
        logger.info(f"当前数据库版本: {current_version}")

        # 按版本号排序执行
        pending = sorted(
            [(v, info) for v, info in MIGRATIONS.items() if v > current_version],
            key=lambda x: x[0],
        )

        if not pending:
            logger.info("数据库已是最新版本，无需迁移")
            return

        logger.info(f"发现 {len(pending)} 个待执行迁移")

        for version, (description, migrate_func) in pending:
            logger.info(f"执行迁移 {version}: {description}")
            try:
                migrate_func(db)
                _record_migration(db, version, description)
                logger.info(f"迁移 {version} 执行成功: {description}")
            except Exception as e:
                logger.error(f"迁移 {version} 执行失败: {e}")
                db.rollback()
                raise RuntimeError(f"迁移 {version} 失败: {e}") from e

        logger.info(f"数据库迁移完成，当前版本: {max(v for v, _ in pending)}")

    finally:
        db.close()


def get_migration_status(engine=None) -> dict:
    """获取迁移状态信息"""
    if engine is None:
        from app.database import engine as default_engine
        engine = default_engine

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        current_version = _get_current_version(db)

        result = db.execute(text(
            "SELECT version, description, applied_at FROM _migrations ORDER BY version"
        ))
        applied = [
            {"version": row[0], "description": row[1], "applied_at": row[2]}
            for row in result.fetchall()
        ]

        pending = [
            {"version": v, "description": info[0]}
            for v, info in sorted(MIGRATIONS.items())
            if v > current_version
        ]

        return {
            "current_version": current_version,
            "total_migrations": len(MIGRATIONS),
            "applied": applied,
            "pending": pending,
        }
    finally:
        db.close()
