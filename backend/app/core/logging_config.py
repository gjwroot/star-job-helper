"""
结构化日志配置模块。

提供按日期轮转的文件日志，不同级别使用不同格式。
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from app.config import get_settings

settings = get_settings()


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器，输出包含时间、级别、模块等结构化信息"""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        # 基础结构化字段
        log_data = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # 添加额外字段
        if self.include_extra:
            # 提取自定义字段
            for attr in ("user_id", "request_id", "ip", "path", "method", "status_code"):
                value = getattr(record, attr, None)
                if value is not None:
                    log_data[attr] = value

        # 异常信息
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)

        # 构建输出字符串
        parts = [f"[{log_data['timestamp']}]"]
        parts.append(f"[{log_data['level']:>8s}]")
        parts.append(f"[{log_data['module']}:{log_data['function']}:{log_data['line']}]")

        # 额外上下文
        extra_parts = []
        for key in ("user_id", "request_id", "ip", "method", "path", "status_code"):
            if key in log_data:
                extra_parts.append(f"{key}={log_data[key]}")
        if extra_parts:
            parts.append("[" + " ".join(extra_parts) + "]")

        parts.append(log_data["message"])

        result = " ".join(parts)

        if "exception" in log_data:
            result += "\n" + log_data["exception"]

        return result


class SimpleFormatter(logging.Formatter):
    """简单日志格式化器，用于控制台输出"""

    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        level = f"{color}{record.levelname:<8s}{self.RESET}"
        message = record.getMessage()

        result = f"[{timestamp}] {level} {record.name} - {message}"

        if record.exc_info and record.exc_info[0] is not None:
            result += "\n" + self.formatException(record.exc_info)

        return result


def setup_logging() -> logging.Logger:
    """
    初始化日志系统。

    - 控制台：彩色简单格式
    - 文件：结构化格式，按天轮转，保留 30 天
    - 错误文件：仅 ERROR 及以上级别
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    log_file_path = settings.LOG_FILE_PATH

    # 确保日志目录存在
    log_dir = os.path.dirname(log_file_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # 获取根 logger
    logger = logging.getLogger("star_job_helper")
    logger.setLevel(log_level)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # ---------- 控制台 Handler ----------
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(SimpleFormatter())
    logger.addHandler(console_handler)

    # ---------- 文件 Handler（所有级别，按天轮转） ----------
    file_handler = TimedRotatingFileHandler(
        filename=log_file_path,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(StructuredFormatter(include_extra=True))
    file_handler.suffix = "%Y-%m-%d.log"
    logger.addHandler(file_handler)

    # ---------- 错误文件 Handler（仅 ERROR 及以上） ----------
    error_log_path = log_file_path.replace(".log", ".error.log")
    error_handler = TimedRotatingFileHandler(
        filename=error_log_path,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter(include_extra=True))
    error_handler.suffix = "%Y-%m-%d.log"
    logger.addHandler(error_handler)

    # 设置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    logger.info("日志系统初始化完成", extra={
        "level": log_level,
        "log_file": log_file_path,
    })

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """获取 logger 实例"""
    base_name = "star_job_helper"
    if name:
        return logging.getLogger(f"{base_name}.{name}")
    return logging.getLogger(base_name)
