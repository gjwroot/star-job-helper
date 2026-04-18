"""
文件上传服务。

提供图片上传接口，支持头像、工作照片等。
限制文件大小 5MB，保存到 uploads/ 目录，返回文件 URL。
"""

import logging
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User

logger = logging.getLogger("star_job_helper.upload")

router = APIRouter(prefix="/api/upload", tags=["文件上传"])

settings = get_settings()

# 允许的图片类型
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}

# 允许的文件类型（扩展名白名单）
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


def _ensure_upload_dir():
    """确保上传目录存在"""
    upload_dir = settings.UPLOAD_DIR
    if not os.path.isabs(upload_dir):
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), upload_dir)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def _generate_filename(original_filename: str, content_type: str) -> str:
    """生成唯一文件名"""
    ext = ALLOWED_IMAGE_TYPES.get(content_type, "")
    if not ext:
        # 从原始文件名提取扩展名
        _, original_ext = os.path.splitext(original_filename)
        if original_ext.lower() in ALLOWED_EXTENSIONS:
            ext = original_ext.lower()
        else:
            ext = ".jpg"  # 默认

    # 使用日期目录 + UUID 文件名
    date_dir = datetime.utcnow().strftime("%Y%m")
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return os.path.join(date_dir, unique_name)


def _validate_image(file: UploadFile) -> None:
    """验证上传文件是否为合法图片"""
    # 检查文件类型
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file.content_type}，仅支持: {', '.join(ALLOWED_IMAGE_TYPES.keys())}",
        )

    # 检查文件扩展名
    if file.filename:
        _, ext = os.path.splitext(file.filename)
        if ext.lower() not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件扩展名: {ext}",
            )


@router.post("/image")
async def upload_image(
    file: UploadFile = File(..., description="上传图片文件"),
    current_user: User = Depends(get_current_user),
):
    """
    上传图片（头像、工作照片等）。

    - 限制文件大小 5MB
    - 支持 JPEG, PNG, GIF, WebP, BMP 格式
    - 返回文件访问 URL
    """
    _validate_image(file)

    # 读取文件内容并检查大小
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制，最大允许 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上传的文件为空",
        )

    # 生成文件名并保存
    upload_dir = _ensure_upload_dir()
    relative_path = _generate_filename(file.filename or "image.jpg", file.content_type)
    full_path = os.path.join(upload_dir, relative_path)

    # 确保子目录存在
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    # 写入文件
    with open(full_path, "wb") as f:
        f.write(content)

    # 生成访问 URL
    file_url = f"/uploads/{relative_path}"

    logger.info(f"用户 {current_user.id} 上传图片: {file_url} ({len(content)} bytes)")

    return {
        "code": 0,
        "message": "上传成功",
        "data": {
            "url": file_url,
            "filename": os.path.basename(relative_path),
            "size": len(content),
            "content_type": file.content_type,
        },
    }


@router.get("/image/list")
def list_user_uploads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户上传的文件列表。
    """
    upload_dir = _ensure_upload_dir()
    user_files = []

    if os.path.exists(upload_dir):
        for root, dirs, files in os.walk(upload_dir):
            for filename in sorted(files, reverse=True):
                ext = os.path.splitext(filename)[1].lower()
                if ext in ALLOWED_EXTENSIONS:
                    relative_path = os.path.relpath(os.path.join(root, filename), upload_dir)
                    file_url = f"/uploads/{relative_path}"
                    file_stat = os.stat(os.path.join(root, filename))
                    user_files.append({
                        "url": file_url,
                        "filename": filename,
                        "size": file_stat.st_size,
                        "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                    })

    # 限制返回数量
    user_files = user_files[:50]

    return {
        "code": 0,
        "message": "success",
        "data": user_files,
    }
