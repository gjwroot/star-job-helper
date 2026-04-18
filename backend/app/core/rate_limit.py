"""
基于内存的简单接口限流器。

支持 IP + 接口维度的限流，使用装饰器形式配置每个接口的限流规则。

使用方式：
    from app.core.rate_limit import rate_limit

    @router.post("/login")
    @rate_limit(max_requests=5, window_seconds=60)
    def login(...):
        ...
"""

import time
from collections import defaultdict
from functools import wraps
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse


class RateLimiter:
    """基于内存的滑动窗口限流器"""

    def __init__(self):
        # 存储结构: { (ip, path): [timestamp1, timestamp2, ...] }
        self._requests: dict[tuple[str, str], list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, ip: str, path: str, max_requests: int, window_seconds: int) -> bool:
        """
        检查请求是否允许通过。

        Args:
            ip: 客户端 IP 地址
            path: 请求路径
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒）

        Returns:
            True 表示允许，False 表示被限流
        """
        now = time.time()
        key = (ip, path)

        with self._lock:
            # 清理过期的请求记录
            self._requests[key] = [
                ts for ts in self._requests[key]
                if now - ts < window_seconds
            ]

            # 检查是否超过限制
            if len(self._requests[key]) >= max_requests:
                return False

            # 记录本次请求
            self._requests[key].append(now)
            return True

    def get_remaining(self, ip: str, path: str, max_requests: int, window_seconds: int) -> int:
        """获取剩余可用请求数"""
        now = time.time()
        key = (ip, path)

        with self._lock:
            self._requests[key] = [
                ts for ts in self._requests[key]
                if now - ts < window_seconds
            ]
            return max(0, max_requests - len(self._requests[key]))

    def cleanup(self, window_seconds: int = 3600) -> int:
        """清理所有过期的请求记录，返回清理数量"""
        now = time.time()
        cleaned = 0

        with self._lock:
            keys_to_remove = []
            for key, timestamps in self._requests.items():
                self._requests[key] = [
                    ts for ts in timestamps
                    if now - ts < window_seconds
                ]
                if not self._requests[key]:
                    keys_to_remove.append(key)
                cleaned += len(timestamps) - len(self._requests[key])

            for key in keys_to_remove:
                del self._requests[key]

        return cleaned


# 全局限流器实例
_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """获取客户端真实 IP 地址，支持代理头"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else "unknown"


def rate_limit(max_requests: int = 60, window_seconds: int = 60):
    """
    接口限流装饰器。

    Args:
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口（秒）

    用法:
        @router.post("/login")
        @rate_limit(max_requests=5, window_seconds=60)
        async def login(request: Request, ...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 从 kwargs 中获取 request 对象
            request = kwargs.get("request")
            if request is None:
                # 尝试从 args 中查找
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                return await func(*args, **kwargs)

            ip = get_client_ip(request)
            path = request.url.path

            if not _limiter.is_allowed(ip, path, max_requests, window_seconds):
                remaining = _limiter.get_remaining(ip, path, max_requests, window_seconds)
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": 429,
                        "message": f"请求过于频繁，请在 {window_seconds} 秒后重试",
                        "data": {
                            "remaining": remaining,
                            "limit": max_requests,
                            "window": window_seconds,
                        },
                    },
                )

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                return func(*args, **kwargs)

            ip = get_client_ip(request)
            path = request.url.path

            if not _limiter.is_allowed(ip, path, max_requests, window_seconds):
                remaining = _limiter.get_remaining(ip, path, max_requests, window_seconds)
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": 429,
                        "message": f"请求过于频繁，请在 {window_seconds} 秒后重试",
                        "data": {
                            "remaining": remaining,
                            "limit": max_requests,
                            "window": window_seconds,
                        },
                    },
                )

            return func(*args, **kwargs)

        # 根据被装饰函数的类型选择包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def get_limiter() -> RateLimiter:
    """获取全局限流器实例"""
    return _limiter
