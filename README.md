# VeinSim

> 为模仿和学习 ToffeeX 而生的项目

VeinSim 是一个面向**计算流体力学（CFD）仿真**的云端拓扑优化平台，灵感来源于 [ToffeeX](https://toffeex.com)。项目旨在通过完整的工程实践，学习和复现 ToffeeX 在热流体组件生成式设计方面的核心能力。

## 功能特性

- **项目管理** — 创建/管理冷板、换热器等热流体设计项目，支持 STL/STEP/IGES 几何文件上传
- **仿真任务** — 提交 OpenFOAM 拓扑优化仿真任务，Celery 异步调度执行
- **实时进度** — 基于 Redis Pub/Sub + WebSocket 的仿真进度实时推送
- **三维可视化** — Three.js 渲染 STL 模型的交互式 3D 视图
- **对象存储** — MinIO 管理仿真几何文件与结果数据
- **JWT 认证** — 完整的用户注册/登录与 Token 鉴权

## 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | React 19 + TypeScript + Vite + Ant Design + Three.js (react-three-fiber) |
| **后端** | FastAPI + SQLAlchemy (async) + Alembic + Pydantic v2 |
| **异步任务** | Celery + Redis |
| **数据库** | PostgreSQL 16 |
| **对象存储** | MinIO |
| **容器化** | Docker Compose |

## 快速开始

### 前置要求

- Docker & Docker Compose
- Git

### 1. 克隆项目

```bash
git clone https://github.com/lusir11/VeinSim.git
cd VeinSim
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

按需修改 `.env` 中的数据库密码、MinIO 密钥、JWT Secret 等配置项。

### 3. 启动所有服务

```bash
docker compose up -d --build
```

首次启动会自动执行数据库迁移和 MinIO Bucket 初始化。

### 4. 访问服务

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:5173 |
| 后端 API 文档 | http://localhost:8000/docs |
| MinIO 控制台 | http://localhost:9001 |

## 项目结构

```
VeinSim/
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/         # REST API 路由
│   │   ├── models/         # SQLAlchemy 数据模型
│   │   ├── schemas/        # Pydantic 请求/响应模型
│   │   ├── services/       # 业务逻辑（认证、MinIO、WebSocket、进度推送）
│   │   ├── solver/         # OpenFOAM 求解器集成
│   │   ├── celery_worker.py
│   │   ├── config.py       # 环境变量配置
│   │   ├── database.py     # 数据库连接
│   │   └── main.py         # 应用入口
│   └── Dockerfile
├── frontend/               # React 前端
│   ├── src/
│   │   ├── api/            # Axios API 客户端
│   │   ├── components/     # UI 组件（布局、Three.js 3D 视图）
│   │   ├── hooks/          # 自定义 Hooks（WebSocket）
│   │   ├── pages/          # 页面组件
│   │   ├── stores/         # Zustand 状态管理
│   │   └── App.tsx
│   └── Dockerfile
├── docker-compose.yml      # 多服务编排
├── .env.example            # 环境变量模板
└── data/                   # 仿真数据目录
```

## 开发模式

### 仅后端开发

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 仅前端开发

```bash
cd frontend
npm install
npm run dev
```

### 求解器模拟模式

在 `.env` 中设置 `SOLVER_MOCK=true`，可在没有安装 OpenFOAM 的环境下进行开发调试，仿真任务会返回模拟数据。

## 环境变量说明

参考 `.env.example`，主要配置项：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `POSTGRES_USER/PASSWORD/DB` | 数据库连接 | `tofeex` / `tofeex_dev_2026` / `tofeex_db` |
| `DATABASE_URL` | SQLAlchemy 连接字符串 | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis 连接 | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Celery Broker | `redis://redis:6379/1` |
| `MINIO_ENDPOINT` | MinIO 地址 | `minio:9000` |
| `SECRET_KEY` | JWT 签名密钥 | `change-me-...` |
| `SOLVER_MOCK` | 模拟求解器模式 | `true` |
| `VITE_API_BASE_URL` | 前端 API 地址 | `http://localhost:8000/api/v1` |

## AI 一键初始化指令

下载代码压缩包后，将以下指令完整复制并发送给 AI 助手（如 Claude、ChatGPT、Cursor 等），AI 会自动帮你完成所有环境安装和项目启动：

---

<details>
<summary><strong>点击展开 AI 初始化指令（复制下方全部内容）</strong></summary>

```
你是一名 DevOps 工程师。请帮我从零启动 VeinSim 项目。严格按照以下步骤依次执行，每步完成后汇报结果，遇到问题立即停止并说明原因。

## 步骤

### 1. 确认项目目录
当前工作目录就是 VeinSim 项目根目录（包含 docker-compose.yml 的目录）。如果不是，请让我先 cd 到正确的目录。

### 2. 检查并安装 Docker
- 执行 `docker --version` 检查 Docker 是否已安装
- 如果未安装：
  - Windows：提示我去 https://www.docker.com/products/docker-desktop/ 下载安装 Docker Desktop，安装后重启终端
  - macOS：同上，下载 Docker Desktop for Mac
  - Linux：执行 `curl -fsSL https://get.docker.com | sh` 安装，然后 `sudo usermod -aG docker $USER`
- 执行 `docker compose version` 确认 Docker Compose V2 可用（如果不可用，尝试 `docker-compose --version`）
- 执行 `docker info` 确认 Docker 守护进程正在运行。如果未运行，提示我启动 Docker Desktop

### 3. 配置环境变量
- 检查项目根目录是否存在 `.env` 文件
- 如果不存在，执行 `cp .env.example .env`（Windows 下用 `copy .env.example .env`）
- 确认 `.env` 文件已生成，读取并确认以下关键变量存在：DATABASE_URL、REDIS_URL、SECRET_KEY、SOLVER_MOCK

### 4. 构建并启动所有服务
- 执行 `docker compose up -d --build`
- 等待所有容器构建完成（首次可能需要几分钟下载镜像）
- 如果构建失败，分析错误日志并尝试修复

### 5. 验证服务健康状态
- 执行 `docker compose ps` 查看所有容器状态
- 确认以下 6 个容器全部处于 running/healthy 状态：
  - veinsim_db (PostgreSQL)
  - veinsim_redis (Redis)
  - veinsim_minio (MinIO)
  - veinsim_backend (FastAPI)
  - veinsim_celery_worker (Celery)
  - veinsim_frontend (Vite/React)
- 如果有容器未就绪，执行 `docker compose logs <容器名>` 查看日志并诊断问题

### 6. 等待后端就绪
- 循环检测后端健康接口：`curl http://localhost:8000/health`（Windows 下如果 curl 不可用，用 PowerShell 的 `Invoke-RestMethod http://localhost:8000/health`）
- 直到返回 `{"status": "ok", ...}` 为止，最多等待 60 秒
- 如果超时，查看后端日志 `docker compose logs backend`

### 7. 打开前端页面
- 用系统命令自动打开浏览器访问前端：
  - Windows: `start http://localhost:5173`
  - macOS: `open http://localhost:5173`
  - Linux: `xdg-open http://localhost:5173`
- 告诉我："VeinSim 已成功启动！前端地址：http://localhost:5173"

### 8. 汇报结果
以表格形式展示：
| 服务 | 地址 | 状态 |
|------|------|------|
| 前端界面 | http://localhost:5173 | ✅/❌ |
| 后端 API | http://localhost:8000/docs | ✅/❌ |
| MinIO 控制台 | http://localhost:9001 | ✅/❌ |
| PostgreSQL | localhost:5432 | ✅/❌ |
| Redis | localhost:6379 | ✅/❌ |

## 常见问题处理
- 端口冲突：如果 5173/8000/5432/6379/9000/9001 端口被占用，执行 `docker compose down` 后找出占用端口的进程并终止，再重新启动
- 构建失败：检查 Docker 磁盘空间和内存，执行 `docker system prune -a` 清理后重试
- 数据库连接失败：确保 db 容器 healthcheck 通过后再启动 backend
```

</details>

---

> **提示**：首次启动需要下载 Docker 镜像（约 1-2 GB），请确保网络畅通。后续启动只需执行 `docker compose up -d` 即可秒级恢复。

## 许可证

本项目仅供学习参考用途。
