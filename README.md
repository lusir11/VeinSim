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

## 许可证

本项目仅供学习参考用途。
