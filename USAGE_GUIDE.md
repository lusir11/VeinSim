# VeinSim 使用教程

> **VeinSim** — 云端原生物理驱动生成式热流体设计平台  
> 基于流体拓扑优化 + AI 自动生成冷板/换热器流道

---

## 目录

1. [环境要求](#1-环境要求)
2. [安装与启动](#2-安装与启动)
3. [注册与登录](#3-注册与登录)
4. [仪表盘 (Dashboard)](#4-仪表盘-dashboard)
5. [项目管理](#5-项目管理)
   - 5.1 [创建项目](#51-创建项目)
   - 5.2 [项目详情配置](#52-项目详情配置)
   - 5.3 [上传几何模型](#53-上传几何模型)
   - 5.4 [配置热源](#54-配置热源)
   - 5.5 [设置热约束与制造约束](#55-设置热约束与制造约束)
6. [仿真运行](#6-仿真运行)
   - 6.1 [启动仿真](#61-启动仿真)
   - 6.2 [实时监控](#62-实时监控)
   - 6.3 [取消仿真](#63-取消仿真)
   - 6.4 [查看结果](#64-查看结果)
7. [API 接口文档](#7-api-接口文档)
8. [MinIO 对象存储管理](#8-minio-对象存储管理)
9. [常用运维命令](#9-常用运维命令)
10. [常见问题排查](#10-常见问题排查)
11. [项目架构概览](#11-项目架构概览)

---

## 1. 环境要求

| 工具 | 最低版本 | 用途 |
|------|---------|------|
| **Docker Desktop** | 4.x+ | 容器化运行全部服务 |
| **Git** | 2.x+ | 克隆项目代码 |
| **浏览器** | Chrome / Edge 最新版 | 访问前端界面 |

> 无需手动安装 Python、Node.js、PostgreSQL、Redis 等——全部由 Docker 容器提供。

---

## 2. 安装与启动

### 2.1 克隆项目

```bash
git clone <repository-url> TofeeX_imitation
cd TofeeX_imitation
```

### 2.2 初始化环境配置

将 `.env.example` 模板复制为 `.env`：

**Linux / macOS:**
```bash
cp .env.example .env
```

**Windows PowerShell:**
```powershell
Copy-Item .env.example .env
```

`.env` 文件已预填好本地开发默认值，**无需修改即可直接启动**。

关键配置项说明：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `POSTGRES_USER` | `tofeex` | 数据库用户名 |
| `POSTGRES_PASSWORD` | `tofeex_dev_2026` | 数据库密码 |
| `POSTGRES_DB` | `tofeex_db` | 数据库名 |
| `MINIO_ROOT_USER` | `minioadmin` | MinIO 管理员用户 |
| `MINIO_ROOT_PASSWORD` | `minioadmin_secret` | MinIO 管理员密码 |
| `SECRET_KEY` | `change-me-to-random-secret-in-production` | JWT 签名密钥（生产环境务必更换） |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | 前端调用后端的 API 地址 |

### 2.3 一键启动

```bash
docker compose up -d --build
```

首次构建需要 3-5 分钟（下载基础镜像 + 安装 Python/Node 依赖），后续启动仅需数秒。

### 2.4 验证服务状态

```bash
docker compose ps
```

预期看到全部 6 个容器处于运行状态：

| 容器名 | 服务 | 端口 | 状态 |
|--------|------|------|------|
| `veinsim_db` | PostgreSQL 数据库 | 5432 | healthy |
| `veinsim_redis` | Redis 缓存/消息队列 | 6379 | healthy |
| `veinsim_minio` | MinIO 对象存储 | 9000 (API) / 9001 (控制台) | healthy |
| `veinsim_backend` | FastAPI 后端 | 8000 | running |
| `veinsim_celery_worker` | Celery 异步工作节点 | — | running |
| `veinsim_frontend` | React 前端 (Vite) | 5173 | running |

### 2.5 访问地址

| 服务 | URL |
|------|-----|
| **前端界面** | http://localhost:5173 |
| **后端 API 文档 (Swagger)** | http://localhost:8000/docs |
| **后端 API 文档 (ReDoc)** | http://localhost:8000/redoc |
| **MinIO 管理控制台** | http://localhost:9001 |

---

## 3. 注册与登录

### 3.1 注册账号

1. 打开浏览器访问 http://localhost:5173
2. 页面自动跳转至登录/注册界面
3. 点击 **Register** 标签页
4. 填写以下信息：
   - **Email**：有效的邮箱地址（用作登录凭证）
   - **Username**：自定义用户名
   - **Password**：至少 6 位字符
5. 点击 **Create Account**

注册成功后自动登录并跳转至仪表盘。

### 3.2 登录

1. 在登录页面选择 **Login** 标签页
2. 输入注册时的 **Email** 和 **Password**
3. 点击 **Sign In**

登录成功后跳转至仪表盘，右上角显示用户信息。

> **认证机制**：系统使用 JWT (JSON Web Token) 认证，Token 有效期 60 分钟，过期后需重新登录。

---

## 4. 仪表盘 (Dashboard)

仪表盘提供平台整体概览：

- **统计卡片**：显示项目总数、仿真总数、已收敛数量、正在运行数量
- **3D 冷板预览**：交互式三维设计域展示（鼠标左键旋转、滚轮缩放、右键平移）
- **Quick Start Guide**：快速入门指引

左侧导航栏包含：
- **Dashboard** — 首页概览
- **Projects** — 项目管理
- **Simulations** — 仿真管理

---

## 5. 项目管理

### 5.1 创建项目

1. 点击左侧导航 **Projects**
2. 点击右上角 **New Project** 按钮
3. 在弹窗中填写：
   - **Name**：项目名称（必填），例如 "CPU 液冷冷板 v2"
   - **Description**：项目描述（选填）
4. 点击确认创建

项目列表会显示所有属于你的项目，支持分页浏览。

### 5.2 项目详情配置

点击项目名称进入详情页，分为左右两栏：

**左栏 — 3D 预览与热源：**
- 3D 设计域预览窗口
- 几何文件信息
- 热源列表管理

**右栏 — 配置表单：**
- 项目基本信息
- 热约束参数
- 制造工艺约束

### 5.3 上传几何模型

在项目详情页的 **3D Preview** 卡片中：

1. 点击 **Replace Geometry** 按钮（或首次的上传区域）
2. 选择本地文件，支持格式：`.stl`、`.step`、`.stp`
3. 上传完成后文件存储在 MinIO 对象存储中

> 几何文件用于定义冷板的初始设计域，拓扑优化将在此基础上自动生成流道。

### 5.4 配置热源

在 **Heat Sources** 卡片中管理热源：

1. 点击 **Add** 按钮添加一个热源
2. 设置热源的三维坐标和功率：
   - **X / Y / Z (m)**：热源在冷板上的位置（单位：米）
   - **Power (W)**：热源功率（单位：瓦特），例如 CPU 芯片 120W
3. 可添加多个热源模拟多芯片布局
4. 点击热源卡片右上角的删除按钮可移除

### 5.5 设置热约束与制造约束

**Project Settings（项目设置）：**

| 字段 | 说明 | 示例值 |
|------|------|--------|
| Name | 项目名称 | CPU Cold Plate v2 |
| Description | 项目描述 | 用于 200W TDP CPU 的液冷冷板 |
| Manufacturing Process | 制造工艺 | Stamping / CNC / Chemical Etching / 3D Print |

**Thermal Constraints（热约束）：**

| 字段 | 说明 | 推荐范围 |
|------|------|---------|
| Coolant Fluid | 冷却液类型 | Water / Ethylene Glycol 50% / Engine Oil / Air |
| Max Temp (K) | 允许最高温度 | 333~363 K（60~90°C） |
| Max Pressure Drop (Pa) | 允许最大压降 | 2000~10000 Pa |
| Inlet Velocity (m/s) | 入口流速 | 0.05~0.5 m/s |

**Manufacturing Constraints（制造约束）：**

| 字段 | 适用工艺 | 说明 |
|------|---------|------|
| Min Feature Size (mm) | 化学蚀刻 / 3D 打印 | 最小可加工特征尺寸 |
| Max Overhang Angle (deg) | 3D 打印 | 最大悬垂角（超过需支撑） |

设置完成后点击 **Save** 保存。

---

## 6. 仿真运行

### 6.1 启动仿真

有两种方式启动仿真：

**方式一：从项目详情页启动（推荐）**

1. 进入目标项目详情页
2. 确认所有约束参数已设置
3. 点击 **Launch Optimization** 按钮
4. 系统自动创建仿真任务并提交至 Celery 队列

**方式二：从仿真列表页启动**

1. 点击左侧导航 **Simulations**
2. 点击右上角 **New Simulation** 按钮
3. 在弹窗中配置：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| Project | 关联项目 | 从下拉列表选择 |
| Solver | 求解器类型 | Adjoint Shape Optimization |
| Inlet Velocity (m/s) | 入口流速 | 0.1 |
| Max Iterations | 最大迭代次数 | 500 |
| Convergence Tolerance | 收敛容差 | 1e-5 |

4. 点击确认启动

**可用求解器：**

| 求解器 | 用途 |
|--------|------|
| **Adjoint Shape Optimization** | 基于伴随法的流体拓扑优化（核心功能） |
| **Conjugate Heat Transfer** | 共轭换热仿真 |
| **Buoyant Simple** | 自然对流仿真 |

### 6.2 实时监控

仿真启动后，可在仿真详情页实时查看进度：

**状态流程：**
```
Queued → Meshing → Running → Converged
                          ↘ Failed
```

| 状态 | 含义 |
|------|------|
| `queued` | 已排队，等待 Celery 工作节点处理 |
| `meshing` | 正在生成计算网格 |
| `running` | 求解器正在迭代运算 |
| `converged` | 优化已收敛，结果可用 |
| `failed` | 仿真失败 |
| `cancelled` | 用户手动取消 |

**实时监控功能：**

- **WebSocket 实时推送**：仿真进度通过 WebSocket 实时推送至前端，无需刷新
- **进度条**：显示当前迭代次数 / 最大迭代次数
- **残差值**：实时显示求解器残差（越小越接近收敛）
- **步骤指示器**：可视化展示 Queued → Meshing → Solving → Converged 四阶段
- **连接状态**：显示 WebSocket 是否已连接

> 系统每 10 秒自动轮询仿真列表状态，每 15 秒轮询详情页状态作为 WebSocket 的备份。

### 6.3 取消仿真

在仿真列表页，对状态为 `running` 或 `queued` 的仿真：

1. 找到对应仿真行
2. 点击 **Cancel** 按钮
3. 系统将撤销 Celery 任务并将状态标记为 `cancelled`

### 6.4 查看结果

仿真收敛后，在仿真详情页可以看到：

- **优化指标**：包括压降、最高温度、体积分数等性能参数
- **收敛信息**：最终残差值、迭代次数、计算耗时
- **3D 结果可视化**：优化后的流道形状（后续版本将集成 VTK.js 温度场/速度场渲染）

---

## 7. API 接口文档

VeinSim 后端提供完整的 RESTful API，并自带交互式文档：

### Swagger UI

访问 http://localhost:8000/docs

- 可直接在浏览器中测试所有 API
- 点击 **Authorize** 按钮输入 JWT Token 进行认证
- Token 格式：`Bearer <your_token>`（从登录接口获取）

### 主要 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 注册新用户 |
| POST | `/api/v1/auth/login` | 登录获取 JWT Token |
| GET | `/api/v1/auth/me` | 获取当前用户信息 |
| POST | `/api/v1/projects` | 创建项目 |
| GET | `/api/v1/projects` | 获取项目列表 |
| GET | `/api/v1/projects/{id}` | 获取项目详情 |
| PATCH | `/api/v1/projects/{id}` | 更新项目 |
| DELETE | `/api/v1/projects/{id}` | 删除项目 |
| POST | `/api/v1/projects/{id}/geometry` | 上传几何文件 |
| POST | `/api/v1/simulations` | 创建并启动仿真 |
| GET | `/api/v1/simulations` | 获取仿真列表 |
| GET | `/api/v1/simulations/{id}` | 获取仿真详情 |
| POST | `/api/v1/simulations/{id}/cancel` | 取消仿真 |
| GET | `/api/v1/simulations/{id}/results` | 获取仿真结果 |
| WS | `/api/v1/ws/simulations/{id}` | WebSocket 实时进度 |

### 认证示例 (curl)

```bash
# 登录获取 Token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your@email.com&password=your_password"

# 使用 Token 访问 API
curl http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 8. MinIO 对象存储管理

MinIO 是 S3 兼容的对象存储服务，用于存储几何文件和仿真结果。

### 访问控制台

浏览器打开 http://localhost:9001

| 字段 | 值 |
|------|-----|
| Username | `minioadmin` |
| Password | `minioadmin_secret` |

### 存储结构

```
tofeex-models/          ← 主存储桶
├── geometries/         ← 用户上传的几何文件
│   └── {project_id}/
│       └── model.stl
├── simulations/        ← 仿真输出文件
│   └── {simulation_id}/
│       ├── porosity.vtu
│       ├── optimized.stl
│       └── residuals.csv
└── ...
```

---

## 9. 常用运维命令

### 启动 / 停止

```bash
# 启动全部服务（后台运行）
docker compose up -d

# 停止全部服务
docker compose down

# 重启某个服务
docker compose restart backend

# 重新构建并启动（代码修改后）
docker compose up -d --build
```

### 查看日志

```bash
# 查看所有服务日志
docker compose logs -f

# 查看后端日志
docker compose logs -f backend

# 查看 Celery Worker 日志
docker compose logs -f celery_worker

# 查看前端日志
docker compose logs -f frontend

# 查看最近 50 行
docker compose logs --tail=50 backend
```

### 数据库操作

```bash
# 进入 PostgreSQL 命令行
docker compose exec db psql -U tofeex -d tofeex_db

# 列出所有表
\dt

# 查询用户
SELECT id, email, username, created_at FROM users;

# 退出 psql
\q
```

### 清理数据（慎用）

```bash
# 停止服务并删除所有数据卷（会清空数据库和文件）
docker compose down -v
```

### 更新代码后重建

```bash
# 拉取最新代码后
docker compose up -d --build
```

---

## 10. 常见问题排查

### Q: 前端显示 "Network Error"

**原因**：后端 API 请求失败。

**排查步骤**：
1. 检查后端是否正在运行：`docker compose ps`
2. 查看后端日志：`docker compose logs backend`
3. 确认 API 可访问：浏览器打开 http://localhost:8000/docs
4. 如果端口 8000 被占用，修改 `.env` 中的端口映射

### Q: 注册/登录失败

**排查步骤**：
1. 确认邮箱未被注册（注册接口返回 400 = 邮箱已存在）
2. 密码至少 6 位
3. 检查后端日志中是否有 bcrypt 相关错误

### Q: 仿真一直显示 "queued"

**原因**：Celery Worker 可能未正常运行。

```bash
# 查看 Worker 日志
docker compose logs celery_worker

# 确认 Worker 状态
docker compose ps celery_worker
```

### Q: 3D 预览无法加载

**排查步骤**：
1. 3D 预览基于 Three.js，需要 WebGL 支持
2. 确认浏览器未禁用硬件加速
3. 尝试更新显卡驱动

### Q: Docker 镜像拉取失败

**原因**：国内网络可能无法直接访问 Docker Hub。

**解决方案**：
1. 使用 VPN / 代理
2. 在 Docker Desktop → Settings → Docker Engine 中添加镜像源：
```json
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
```
3. 保存后重启 Docker Desktop

### Q: 端口被占用

如果 5432 / 6379 / 8000 / 5173 等端口已被其他程序占用：

1. 停止占用端口的程序
2. 或修改 `docker-compose.yml` 中的端口映射，例如将前端端口改为 5174：
```yaml
    ports:
      - "5174:5173"
```

---

## 11. 项目架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│              Vite + TypeScript + Ant Design              │
│           Three.js 3D 可视化 + WebSocket 实时通信          │
│                    :5173                                 │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────▼──────────────────────────────────┐
│                   Backend (FastAPI)                      │
│           JWT 认证 · SQLAlchemy ORM · RESTful API         │
│              WebSocket Server · MinIO Client              │
│                    :8000                                 │
└────┬──────────┬──────────┬──────────────────────────────┘
     │          │          │
┌────▼────┐ ┌──▼───┐ ┌────▼─────┐
│PostgreSQL│ │Redis │ │  MinIO   │
│  :5432   │ │:6379 │ │:9000/9001│
│ 用户/项目 │ │缓存/  │ │ 文件存储  │
│ /仿真数据 │ │消息队列│ │ STL/VTU  │
└──────────┘ └──┬───┘ └──────────┘
                │
        ┌───────▼────────┐
        │ Celery Worker   │
        │ OpenFOAM 求解器  │
        │ 拓扑优化引擎     │
        │ 后处理管线       │
        └────────────────┘
```

**技术栈一览：**

| 层级 | 技术选型 |
|------|---------|
| 前端框架 | React 19 + TypeScript + Vite |
| UI 组件库 | Ant Design 5 |
| 3D 可视化 | Three.js + @react-three/fiber |
| 状态管理 | Zustand |
| 后端框架 | FastAPI 0.115 + Uvicorn |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| 任务队列 | Celery 5.4 + Redis |
| 数据库 | PostgreSQL 16 |
| 对象存储 | MinIO (S3 兼容) |
| 容器化 | Docker Compose |
| 求解器 | OpenFOAM (adjointShapeOptimizationFoam) |
| 后处理 | SciPy + scikit-image + trimesh + VTK |
