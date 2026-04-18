# ⭐ 星职助手 (Star Job Helper)

> 面向心智障碍群体的职场任务引导工具，让每一颗星星都能在职场闪耀。

## 📖 项目简介

**星职助手**是一款专为心智障碍群体设计的职场辅助工具。通过分步任务引导、情绪追踪、AI 沟通辅助等功能，帮助心智障碍人士更好地适应职场环境，提升独立工作能力，同时为就业辅导员提供数据支持，实现精准辅导。

## ✨ 功能特性

### 六大核心功能

| 功能 | 描述 |
|------|------|
| 📋 **分步任务引导** | 将复杂工作拆解为简单步骤，逐步引导完成，支持自定义任务模板 |
| 😊 **情绪追踪记录** | 记录每日情绪变化，自动生成情绪趋势图，提供情绪调节小贴士 |
| 🤖 **AI 沟通助手** | 智能生成职场沟通语句，提供场景化表达建议（打招呼、求助、表达情绪等） |
| ⏱️ **工作计时器** | 内置番茄钟计时器，帮助管理工作时间与休息节奏 |
| 🏆 **成就激励系统** | 完成任务获得星星奖励，解锁成就徽章，正向激励持续进步 |
| 📊 **数据可视化** | Chart.js 图表展示任务完成趋势、情绪变化曲线、每周数据统计 |

### AI 能力

- **聊天陪伴**：基于关键词匹配 + 情绪上下文的规则引擎，提供温暖的对话陪伴
- **沟通语句生成**：根据职场场景（问候、求助、表达情绪等）智能生成合适的沟通语句
- **每日总结**：自动汇总当日任务完成情况、情绪变化，生成个性化鼓励语
- **自适应难度**：根据近 7 天任务完成率和情绪状态，智能建议任务难度调整

### PWA 支持

- 支持添加到主屏幕，像原生应用一样使用
- 离线缓存，无网络环境也可使用基础功能
- 响应式设计，适配手机和平板

## 🛠️ 技术栈

### 后端

| 技术 | 说明 |
|------|------|
| [FastAPI](https://fastapi.tiangolo.com/) | 高性能异步 Web 框架 |
| [SQLite](https://www.sqlite.org/) | 轻量级关系数据库 |
| [SQLAlchemy](https://www.sqlalchemy.org/) | ORM 数据库操作 |
| [JWT](https://jwt.io/) | JSON Web Token 身份认证 |
| [Pydantic](https://docs.pydantic.dev/) | 数据校验与序列化 |
| [APScheduler](https://apscheduler.readthedocs.io/) | 定时任务调度 |

### 前端

| 技术 | 说明 |
|------|------|
| [Vue 3](https://vuejs.org/) | 渐进式 JavaScript 框架（CDN 模式） |
| [Tailwind CSS](https://tailwindcss.com/) | 原子化 CSS 框架 |
| [Chart.js](https://www.chartjs.org/) | 数据可视化图表库 |
| [Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API) | 浏览器原生语音识别 |

### 安全特性

- CSP 安全头（Content-Security-Policy）
- XSS 防护中间件（输入过滤）
- CSRF Token 防护
- JWT Token 认证
- SQL 注入防护（SQLAlchemy ORM 参数化查询）
- 接口限流（Rate Limiting）
- 密码 bcrypt 加密存储

## 📁 项目结构

```
star-job-helper/
├── backend/                    # 后端服务
│   ├── main.py                 # FastAPI 应用入口
│   ├── requirements.txt        # Python 依赖
│   ├── app/
│   │   ├── config.py           # 应用配置（支持环境变量）
│   │   ├── database.py         # 数据库连接与会话管理
│   │   ├── api/                # API 路由
│   │   │   ├── auth.py         # 认证接口（注册/登录）
│   │   │   ├── tasks.py        # 任务接口（模板/我的任务）
│   │   │   ├── moods.py        # 情绪接口（记录/历史）
│   │   │   ├── achievements.py # 成就接口
│   │   │   ├── admin.py        # 管理后台接口
│   │   │   ├── upload.py       # 文件上传接口
│   │   │   └── ai.py           # AI 接口（聊天/沟通/总结）
│   │   ├── models/             # 数据模型
│   │   │   ├── user.py         # 用户模型
│   │   │   ├── task.py         # 任务模型（模板/用户任务/每日统计）
│   │   │   ├── mood.py         # 情绪记录模型
│   │   │   └── achievement.py  # 成就模型
│   │   ├── services/           # 业务逻辑层
│   │   │   ├── auth_service.py
│   │   │   ├── task_service.py
│   │   │   ├── mood_service.py
│   │   │   ├── achievement_service.py
│   │   │   ├── ai_service.py   # AI 规则引擎
│   │   │   └── scheduler_service.py  # 定时任务
│   │   └── core/               # 核心模块
│   │       ├── deps.py         # 依赖注入（认证/角色鉴权）
│   │       ├── security.py     # 安全工具（加密/CSRF/XSS）
│   │       ├── rate_limit.py   # 接口限流
│   │       ├── logging_config.py  # 日志配置
│   │       └── migrate.py      # 数据库迁移
│   ├── tests/                  # 单元测试
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_tasks.py
│   │   └── test_moods.py
│   └── logs/                   # 日志文件
├── frontend/                   # 前端应用
│   ├── index.html              # 主应用（用户端 SPA）
│   ├── admin.html              # 管理后台
│   ├── demo.html               # 参赛展示页面
│   └── public/
│       └── manifest.json       # PWA 配置
├── docker/                     # Docker 部署
│   ├── Dockerfile              # 后端镜像
│   ├── docker-compose.yml      # 编排配置
│   ├── nginx.conf              # Nginx 反向代理
│   └── .env.example            # 环境变量示例
├── docs/                       # 项目文档
│   ├── user-guide.md           # 用户使用手册
│   └── counselor-guide.md      # 辅导员使用指南
└── README.md                   # 项目说明（本文件）
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 现代浏览器（Chrome / Edge / Safari）

### 安装依赖

```bash
# 进入后端目录
cd backend

# 安装 Python 依赖
pip install -r requirements.txt
```

### 启动后端

```bash
cd backend
python main.py
```

后端服务将在 `http://localhost:8000` 启动。

### 打开前端

直接在浏览器中打开 `frontend/index.html` 即可使用。

> **提示**：前端默认连接 `http://localhost:8000` 的后端 API。如需修改，请编辑 `index.html` 中的 API 基础地址。

## 📡 API 文档

后端启动后，访问以下地址查看完整 API 文档：

| 文档 | 地址 |
|------|------|
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| OpenAPI JSON | http://localhost:8000/openapi.json |

### 主要 API 端点

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | `POST /api/auth/register` | 用户注册 |
| 认证 | `POST /api/auth/login` | 用户登录 |
| 任务 | `GET /api/tasks/templates` | 获取任务模板 |
| 任务 | `POST /api/tasks/my` | 创建我的任务 |
| 任务 | `POST /api/tasks/{id}/step` | 完成/取消步骤 |
| 情绪 | `POST /api/moods/record` | 记录情绪 |
| 情绪 | `GET /api/moods/history` | 情绪历史 |
| 成就 | `GET /api/achievements` | 我的成就 |
| AI | `POST /api/ai/chat` | AI 聊天陪伴 |
| AI | `POST /api/ai/comm-speech` | 生成沟通语句 |
| AI | `GET /api/ai/daily-summary` | 每日总结 |
| AI | `GET /api/ai/difficulty-suggestion` | 难度建议 |
| 仪表盘 | `GET /api/stats/dashboard` | 个人仪表盘 |
| 管理 | `GET /api/admin/users` | 用户管理 |
| 管理 | `GET /api/admin/stats` | 全局统计 |
| 管理 | `GET /api/admin/mood-stats` | 情绪统计 |

## 🐳 Docker 部署

### 使用 Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/your-username/star-job-helper.git
cd star-job-helper

# 2. 配置环境变量
cp docker/.env.example docker/.env
# 编辑 .env 修改 SECRET_KEY 等配置

# 3. 启动服务
cd docker
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

服务启动后：
- 前端：http://localhost
- 后端 API：http://localhost:8000
- API 文档：http://localhost/docs

### 手动构建

```bash
# 构建后端镜像
cd docker
docker build -t star-job-helper-backend .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -v ./data:/app/data \
  -e SECRET_KEY=your-secret-key \
  star-job-helper-backend
```

## 📸 截图

> 以下为应用界面说明（截图待补充）

### 用户端主页
![用户端主页](docs/screenshots/home.png)
*展示任务列表、今日统计、快捷操作入口的主界面*

### 分步任务引导
![分步任务](docs/screenshots/task.png)
*将复杂任务拆解为可视化步骤，逐步勾选完成*

### 情绪追踪
![情绪追踪](docs/screenshots/mood.png)
*选择情绪表情记录心情，查看情绪趋势图表*

### AI 沟通助手
![AI助手](docs/screenshots/ai-chat.png)
*与 AI 小助手对话，获取职场沟通建议*

### 管理后台
![管理后台](docs/screenshots/admin.png)
*辅导员/管理员查看用户数据、情绪统计、任务完成情况*

## 👥 用户角色

| 角色 | 说明 |
|------|------|
| **user**（普通用户） | 心智障碍人士，使用任务引导、情绪记录等功能 |
| **counselor**（辅导员） | 就业辅导员，管理用户、创建任务模板、查看数据 |
| **admin**（管理员） | 系统管理员，拥有所有权限 |

## 🤝 贡献指南

我们欢迎任何形式的贡献！无论是代码、文档、建议还是 Bug 报告。

### 如何贡献

1. **Fork** 本仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'feat: 添加某功能'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 **Pull Request**

### 提交规范

请遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- `feat:` 新功能
- `fix:` 修复 Bug
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具链更新

### 开发环境

```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行测试
cd backend
pytest tests/ -v

# 启动开发服务器（热重载）
python main.py
```

## 📄 许可证

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 开源。

```
MIT License

Copyright (c) 2025 Star Job Helper

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

## 🙏 致谢

- 感谢所有关注心智障碍群体就业的社会力量
- 感谢 TRAE AI 辅助开发工具的支持
- 本项目为 TRAE x 脉脉「AI 无限职场」SOLO 挑战赛参赛作品
