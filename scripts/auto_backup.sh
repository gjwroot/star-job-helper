#!/bin/bash
# ============================================================
# Star Job Helper - 数据库自动备份脚本
# ============================================================
# 建议配合 cron 使用：
#   0 2 * * * /path/to/scripts/auto_backup.sh >> /path/to/logs/backup.log 2>&1
#
# 功能：
#   1. 创建带时间戳的数据库备份
#   2. 自动清理超过7天的旧备份
#   3. 记录备份日志
# ============================================================

set -euo pipefail

# ---------- 配置 ----------
# 脚本所在目录的上级目录作为项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backend/backups"
DB_PATH="${PROJECT_ROOT}/backend/star_job_helper.db"
RETENTION_DAYS=7
LOG_FILE="${PROJECT_ROOT}/backend/logs/backup.log"

# ---------- 前置检查 ----------
if [ ! -f "$DB_PATH" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: 数据库文件不存在: $DB_PATH" >> "$LOG_FILE" 2>&1
    exit 1
fi

# 创建备份目录
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# ---------- 创建备份 ----------
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
FILENAME="starjob_backup_${TIMESTAMP}.db"
BACKUP_PATH="${BACKUP_DIR}/${FILENAME}"

cp "$DB_PATH" "$BACKUP_PATH"

# 检查备份是否成功
if [ ! -f "$BACKUP_PATH" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: 备份创建失败" >> "$LOG_FILE" 2>&1
    exit 1
fi

BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: 备份创建成功: $FILENAME (大小: $BACKUP_SIZE)" >> "$LOG_FILE"

# ---------- 清理过期备份 ----------
DELETED_COUNT=0
find "$BACKUP_DIR" -name "starjob_backup_*.db" -mtime +$RETENTION_DAYS -type f | while read -r old_file; do
    rm -f "$old_file"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: 已删除过期备份: $(basename "$old_file")" >> "$LOG_FILE"
    DELETED_COUNT=$((DELETED_COUNT + 1))
done

# ---------- 输出摘要 ----------
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "starjob_backup_*.db" -type f | wc -l)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: 当前备份数量: $TOTAL_BACKUPS" >> "$LOG_FILE"
echo "Backup created: $FILENAME (size: $BACKUP_SIZE, total backups: $TOTAL_BACKUPS)"
