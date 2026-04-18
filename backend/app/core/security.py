import html
import re
import secrets
import string
from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

# ---------- 密码相关 ----------


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 加密"""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ---------- JWT Token ----------


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """创建 JWT Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    """解码 JWT Token，返回 payload 或 None"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


# ---------- 输入验证和清洗 ----------

# SQL 注入关键词模式
SQL_INJECTION_PATTERNS = re.compile(
    r"(?:--|;|/\*|\*/|xp_|sp_|exec\s|execute\s|"
    r"select\s|insert\s|update\s|delete\s|drop\s|"
    r"alter\s|create\s|truncate\s|union\s|"
    r"0x[0-9a-fA-F]+|char\s*\(|concat\s*\(|"
    r"information_schema|sys\s|mysql\s|pg_)",
    re.IGNORECASE,
)

# XSS 危险标签模式
XSS_DANGEROUS_PATTERNS = re.compile(
    r"<\s*script|<\s*iframe|<\s*object|<\s*embed|"
    r"<\s*applet|<\s*form|<\s*input|"
    r"javascript\s*:|vbscript\s*:|on\w+\s*=",
    re.IGNORECASE,
)


def sanitize_input(value: str) -> str:
    """
    清洗用户输入，防止 XSS 攻击。
    - 转义 HTML 特殊字符
    - 移除危险标签和事件属性
    - 去除首尾空白
    """
    if not isinstance(value, str):
        return value

    # 去除首尾空白
    value = value.strip()

    # 移除 null 字节
    value = value.replace("\x00", "")

    # 检测并移除 XSS 危险模式
    if XSS_DANGEROUS_PATTERNS.search(value):
        value = XSS_DANGEROUS_PATTERNS.sub("", value)

    # HTML 实体转义
    value = html.escape(value, quote=True)

    return value


def validate_no_sql_injection(value: str) -> bool:
    """
    检测输入中是否包含 SQL 注入特征。
    返回 True 表示安全，False 表示可能存在注入风险。

    注意：本项目已通过 SQLAlchemy ORM 参数化查询实现 SQL 注入防护，
    此函数作为额外安全层用于日志记录和告警。
    """
    if not isinstance(value, str):
        return True

    return not bool(SQL_INJECTION_PATTERNS.search(value))


def sanitize_dict(data: dict) -> dict:
    """递归清洗字典中所有字符串值"""
    cleaned = {}
    for key, value in data.items():
        if isinstance(value, str):
            cleaned[key] = sanitize_input(value)
        elif isinstance(value, dict):
            cleaned[key] = sanitize_dict(value)
        elif isinstance(value, list):
            cleaned[key] = [
                sanitize_input(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned


# ---------- CSRF Token ----------

# 内存存储的 CSRF Token（生产环境应使用 Redis）
_csrf_tokens: dict[str, datetime] = {}


def generate_csrf_token() -> str:
    """
    生成 CSRF Token。
    返回 32 字符的随机安全字符串。
    """
    alphabet = string.ascii_letters + string.digits
    token = "".join(secrets.choice(alphabet) for _ in range(32))
    _csrf_tokens[token] = datetime.utcnow()
    return token


def validate_csrf_token(token: str) -> bool:
    """
    验证 CSRF Token 是否有效。
    Token 有效期为 1 小时。
    """
    if not token or token not in _csrf_tokens:
        return False

    created_at = _csrf_tokens[token]
    if datetime.utcnow() - created_at > timedelta(hours=1):
        # 过期，移除
        del _csrf_tokens[token]
        return False

    return True


def remove_csrf_token(token: str) -> None:
    """移除已使用的 CSRF Token（一次性使用）"""
    _csrf_tokens.pop(token, None)


def cleanup_expired_csrf_tokens() -> int:
    """清理过期的 CSRF Token，返回清理数量"""
    now = datetime.utcnow()
    expired = [
        token for token, created_at in _csrf_tokens.items()
        if now - created_at > timedelta(hours=1)
    ]
    for token in expired:
        del _csrf_tokens[token]
    return len(expired)
