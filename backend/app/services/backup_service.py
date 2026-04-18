import logging
import os
import shutil
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BackupService:
    """数据库备份服务"""

    @staticmethod
    def create_backup(db_path: str, backup_dir: str = "./backups") -> str:
        """
        创建数据库备份（复制SQLite文件到备份目录）。

        Args:
            db_path: 数据库文件路径
            backup_dir: 备份目录路径

        Returns:
            str: 备份文件完整路径

        Raises:
            FileNotFoundError: 数据库文件不存在
            OSError: 文件操作失败
        """
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")

        os.makedirs(backup_dir, exist_ok=True)

        filename = f"starjob_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = os.path.join(backup_dir, filename)

        shutil.copy2(db_path, backup_path)

        logger.info(f"数据库备份已创建: {backup_path}")
        return backup_path

    @staticmethod
    def list_backups(backup_dir: str = "./backups") -> list[dict]:
        """
        列出所有备份文件。

        Args:
            backup_dir: 备份目录路径

        Returns:
            list[dict]: 备份文件列表，每个元素包含 filename, size, created_at
        """
        backups = []

        if not os.path.exists(backup_dir):
            return backups

        for filename in sorted(os.listdir(backup_dir), reverse=True):
            if filename.startswith("starjob_backup_") and filename.endswith(".db"):
                filepath = os.path.join(backup_dir, filename)
                stat = os.stat(filepath)
                backups.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })

        return backups

    @staticmethod
    def restore_backup(backup_path: str, db_path: str, backup_dir: str = "./backups") -> str:
        """
        从备份恢复数据库。

        恢复前会自动创建当前数据库的备份。

        Args:
            backup_path: 备份文件路径
            db_path: 数据库文件路径
            backup_dir: 备份目录路径（用于存放恢复前的备份）

        Returns:
            str: 恢复前备份的文件路径

        Raises:
            FileNotFoundError: 备份文件不存在
            OSError: 文件操作失败
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")

        os.makedirs(backup_dir, exist_ok=True)

        # 恢复前先备份当前数据库
        pre_restore_filename = f"starjob_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        pre_restore_path = os.path.join(backup_dir, pre_restore_filename)

        if os.path.exists(db_path):
            shutil.copy2(db_path, pre_restore_path)

        # 执行恢复
        shutil.copy2(backup_path, db_path)

        logger.info(f"数据库已从备份恢复: {backup_path}")
        return pre_restore_path

    @staticmethod
    def auto_backup(db_path: str, backup_dir: str = "./backups", retention_days: int = 7) -> str | None:
        """
        自动备份（保留最近N天的备份）。

        Args:
            db_path: 数据库文件路径
            backup_dir: 备份目录路径
            retention_days: 保留天数（默认7天）

        Returns:
            str | None: 新创建的备份路径，失败时返回 None
        """
        try:
            # 创建新备份
            backup_path = BackupService.create_backup(db_path, backup_dir)

            # 清理过期备份
            if os.path.exists(backup_dir):
                cutoff_time = datetime.now() - timedelta(days=retention_days)
                for filename in os.listdir(backup_dir):
                    if filename.startswith("starjob_backup_") and filename.endswith(".db"):
                        filepath = os.path.join(backup_dir, filename)
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                        if file_mtime < cutoff_time:
                            os.remove(filepath)
                            logger.info(f"已删除过期备份: {filename}")

            return backup_path

        except Exception as e:
            logger.error(f"自动备份失败: {e}")
            return None
