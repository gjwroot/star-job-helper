from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置，支持环境变量覆盖"""

    APP_NAME: str = "Star Job Helper"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库
    DATABASE_URL: str = "sqlite:///./star_job_helper.db"

    # JWT
    SECRET_KEY: str = "star-job-helper-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7

    # 数据库备份路径
    DB_BACKUP_PATH: str = "./backups"

    # 日志级别: DEBUG / INFO / WARNING / ERROR / CRITICAL
    LOG_LEVEL: str = "INFO"

    # 日志文件路径
    LOG_FILE_PATH: str = "./logs/app.log"

    # 允许的 CORS 源（逗号分隔），默认允许所有
    CORS_ORIGINS: str = "*"

    # 文件上传
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB

    # 限流配置
    RATE_LIMIT_LOGIN: int = 5  # 登录接口：5次/分钟
    RATE_LIMIT_DEFAULT: int = 60  # 普通接口：60次/分钟

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
