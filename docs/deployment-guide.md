# Star Job Helper - 生产环境部署指南

## 1. HTTPS 强制配置

在生产环境中，必须使用 HTTPS 来保护用户数据传输安全。以下是使用 Nginx + Let's Encrypt 的配置方案。

---

## 2. Nginx HTTPS 配置示例

### 2.1 安装 Nginx

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx -y

# CentOS/RHEL
sudo yum install nginx -y
```

### 2.2 Nginx 配置文件

创建配置文件 `/etc/nginx/sites-available/star-job-helper`：

```nginx
# HTTP -> HTTPS 强制跳转
server {
    listen 80;
    server_name your-domain.com;

    # Let's Encrypt 证书验证路径
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # 所有其他请求跳转到 HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS 主配置
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书路径（Let's Encrypt）
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS（强制 HTTPS，有效期 1 年）
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # 安全头
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 日志
    access_log /var/log/nginx/star-job-helper-access.log;
    error_log /var/log/nginx/star-job-helper-error.log;

    # 前端静态文件
    location / {
        root /path/to/star-job-helper/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持（如需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 上传文件大小限制
    client_max_body_size 10M;

    # 静态资源缓存
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 2.3 启用配置

```bash
sudo ln -s /etc/nginx/sites-available/star-job-helper /etc/nginx/sites-enabled/
sudo nginx -t          # 测试配置语法
sudo systemctl reload nginx
```

---

## 3. Let's Encrypt 证书申请

### 3.1 安装 Certbot

```bash
# Ubuntu/Debian
sudo apt install certbot python3-certbot-nginx -y

# CentOS/RHEL
sudo yum install certbot python3-certbot-nginx -y
```

### 3.2 申请证书

```bash
# 首次申请（自动修改 Nginx 配置）
sudo certbot --nginx -d your-domain.com

# 仅获取证书（手动配置）
sudo certbot certonly --webroot -w /var/www/certbot -d your-domain.com
```

### 3.3 自动续期

Certbot 会自动创建定时任务，可通过以下命令验证：

```bash
# 测试续期
sudo certbot renew --dry-run

# 查看定时任务
sudo systemctl status certbot.timer
```

---

## 4. 安全部署检查清单

部署到生产环境前，请逐项确认以下安全措施：

### 4.1 基础安全

- [ ] **HTTPS 已启用**：所有流量通过 HTTPS 传输
- [ ] **HSTS 已配置**：强制浏览器使用 HTTPS
- [ ] **域名已备案**：如需在中国大陆部署，确保域名已完成 ICP 备案

### 4.2 应用安全

- [ ] **SECRET_KEY 已更换**：修改 `SECRET_KEY` 为强随机字符串
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- [ ] **DEBUG 模式已关闭**：设置 `DEBUG=False`
- [ ] **CORS 已限制**：设置 `CORS_ORIGINS` 为具体域名，不使用 `*`
- [ ] **数据库文件权限**：确保 `.db` 文件仅应用进程可读写
  ```bash
  chmod 600 backend/star_job_helper.db
  ```

### 4.3 服务器安全

- [ ] **防火墙已配置**：仅开放 80 和 443 端口
  ```bash
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  sudo ufw enable
  ```
- [ ] **SSH 密钥登录**：禁用密码登录，使用密钥认证
- [ ] **自动安全更新**：启用系统自动安全更新
  ```bash
  sudo apt install unattended-upgrades -y
  sudo dpkg-reconfigure -plow unattended-upgrades
  ```
- [ ] **日志监控**：配置日志轮转和监控告警

### 4.4 数据安全

- [ ] **数据库备份已配置**：设置自动备份定时任务
  ```bash
  crontab -e
  # 添加：0 2 * * * /path/to/scripts/auto_backup.sh
  ```
- [ ] **备份文件权限**：确保备份目录仅管理员可访问
  ```bash
  chmod 700 backend/backups
  ```
- [ ] **GDPR 合规**：确认数据导出和删除接口可用

### 4.5 性能与可靠性

- [ ] **进程管理器**：使用 systemd 或 supervisor 管理应用进程
- [ ] **日志轮转**：配置 logrotate 防止日志文件过大
- [ ] **健康检查**：确认 `/health` 端点正常响应
- [ ] **资源限制**：设置合理的内存和 CPU 限制

---

## 5. 生产环境配置建议

### 5.1 环境变量配置 (`.env`)

```env
# 应用配置
DEBUG=False
SECRET_KEY=your-strong-random-secret-key-here
CORS_ORIGINS=https://your-domain.com

# 数据库
DATABASE_URL=sqlite:///./star_job_helper.db

# JWT
SECRET_KEY=your-jwt-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_DAYS=7

# 日志
LOG_LEVEL=WARNING
LOG_FILE_PATH=./logs/app.log

# 备份
DB_BACKUP_PATH=./backups

# 文件上传
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=5242880
```

### 5.2 Systemd 服务配置

创建 `/etc/systemd/system/star-job-helper.service`：

```ini
[Unit]
Description=Star Job Helper Backend
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/star-job-helper/backend
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
Environment=DEBUG=False

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable star-job-helper
sudo systemctl start star-job-helper
sudo systemctl status star-job-helper
```

### 5.3 日志轮转配置

创建 `/etc/logrotate.d/star-job-helper`：

```
/path/to/star-job-helper/backend/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload star-job-helper > /dev/null 2>&1 || true
    endscript
}
```

### 5.4 Docker 部署（可选）

如果使用 Docker 部署，请参考项目中的 `docker/` 目录：

```bash
cd docker
cp .env.example .env
# 编辑 .env 文件
docker-compose up -d
```

---

## 6. 常见问题

### Q: 证书申请失败怎么办？

1. 确保域名已正确解析到服务器 IP
2. 确保 80 端口可正常访问
3. 检查防火墙是否放行 80 端口
4. 查看 certbot 日志：`sudo cat /var/log/letsencrypt/letsencrypt.log`

### Q: 如何查看应用日志？

```bash
# Systemd 日志
sudo journalctl -u star-job-helper -f

# 应用日志
tail -f /path/to/star-job-helper/backend/logs/app.log
```

### Q: 如何手动触发备份？

通过管理后台 API：
```bash
curl -X POST https://your-domain.com/api/admin/backup \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

或直接运行备份脚本：
```bash
bash /path/to/scripts/auto_backup.sh
```
