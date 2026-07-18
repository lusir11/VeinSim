# ToffeeX 仿制 — 综合技术实施计划

> 目标：构建一个基于物理驱动的云端生成式设计平台，面向热流体组件（冷板、换热器、歧管）的拓扑优化与 generative AI 设计。

---

## A. 最小可行技术栈（MVP Minimum Viable Stack）

| 层级 | 推荐技术 | 备选方案 | 说明 |
|------|----------|----------|------|
| **CFD/热流体求解器** | OpenFOAM (v2412) | SU2 (斯坦福) | 开源、内置伴随求解器、支持拓扑优化 |
| **拓扑优化算法** | SIMP + 伴随法 (自研, 基于 OpenFOAM) | DAFoam / pyTop | 直接在 OpenFOAM 上扩展 |
| **几何内核** | OpenCASCADE (OCCT) | 可选 Chil3D 方案 | 支持 STEP/IGES 导入导出, B-Rep 建模 |
| **Web 3D 查看器** | VTK.js + Three.js | 纯 Three.js | VTK.js 适合科学数据可视化 |
| **前端框架** | React + TypeScript | Vue 3 + TypeScript | 生态成熟, 与 VTK.js/Three.js 集成方便 |
| **后端框架** | Python FastAPI | Go / Rust (性能敏感模块) | 与科学计算生态对接 |
| **任务调度** | Celery + Redis | Temporal | 管理长时间 CFD 计算任务 |
| **云平台** | AWS (EC2 HPC + S3 + RDS) | 阿里云 / Azure | HPC 实例用于求解 |
| **数据库** | PostgreSQL + MinIO (对象存储) | MongoDB | 结构化数据 + 大文件存储 |
| **容器化** | Docker + Kubernetes | Docker Compose (MVP 阶段) | 弹性伸缩计算节点 |

---

## B. 核心技术模块详解

### B1. CFD / 流体求解器

#### 选项对比

| 工具 | 类型 | 许可证 | 拓扑优化支持 | 热-流耦合 | 成熟度 |
|------|------|--------|-------------|-----------|--------|
| **OpenFOAM** | 开源 CFD | GPL | ✅ 内置 adjointShapeOptimizationFoam | ✅ chtMultiRegionFoam | ★★★★★ |
| **SU2** | 开源 CFD | LGPL | ✅ 内置伴随 + 形状优化 | ✅ | ★★★★☆ |
| **DAFoam** | 开源伴随框架 | GPL v3 | ✅ 多学科离散伴随 | ✅ (通过 OpenFOAM) | ★★★★☆ |
| **pyTop** | 开源 Python TO | MIT | ✅ ~200 行代码实现流-热耦合 | ✅ | ★★★☆☆ |
| **COMSOL** | 商业 | 商用许可 | ✅ 内置拓扑优化模块 | ✅ | ★★★★★ |
| **Ansys Fluent** | 商业 | 商用许可 | 有限 (通过 TOSCA) | ✅ | ★★★★★ |

#### 推荐方案：OpenFOAM + 自研优化扩展

**核心能力：**
- **adjointShapeOptimizationFoam**：OpenFOAM v7+ 内置的伴随拓扑优化求解器，通过 Darcy 力模型（孔隙率 α∈[0,1]）描述流固分布
- **rhoSimpleFoam / chtMultiRegionFoam**：共轭换热求解器，处理流-热耦合
- **连续伴随法（Continuous Adjoint Method）**：推导伴随方程，高效计算目标函数梯度
- **MMA 优化器（Method of Moving Asymptotes）**：耦合为设计变量更新算法

**实现路径：**
```
1. 基于 OpenFOAM v2412 搭建基础 CFD 求解器
2. 扩展 adjointShapeOptimizationFoam 为热-流耦合拓扑优化
3. 引入 Helmholtz 密度滤波 + Heaviside 投影 (消除灰度区域)
4. 集成 MMA 优化器 (C++ 编译为动态库)
5. 封装为可调用的微服务 (REST API)
```

**技术难度：★★★★★（极高）**
- 需要深入理解 Navier-Stokes 方程、伴随方法、拓扑优化理论
- 流-热耦合的伴随方程推导复杂（需考虑变热物性）
- 收敛性调优、数值稳定性处理（滤波/投影技术）
- 预计核心开发周期：**6-12 个月**（1-2 名 CFD 专家）

---

### B2. 拓扑优化算法

#### 主流算法对比

| 算法 | 原理 | 优势 | 劣势 | 适用场景 |
|------|------|------|------|----------|
| **SIMP（固体各向同性材料惩罚法）** | 密度法, α∈[0,1], 惩罚中间密度 | 实现简单、计算效率高 | 灰度区域、边界模糊 | MVP 首选，结构 + 流体 |
| **Level Set（水平集法）** | 隐式界面追踪, φ=0 为边界 | 清晰边界、可控制拓扑变化 | 实现复杂、需再初始化 | 需要精确边界的场景 |
| **BESO（双向进化结构优化）** | 添加/移除单元 | 概念简单 | 收敛性差 | 研究探索 |
| **MMC（可移动变形组件法）** | 参数化组件描述结构 | 设计变量少、边界清晰 | 复杂拓扑受限 | 参数化设计 |
| **Phase Field（相场法）** |  diffuse interface | 数学严格 | 计算量大 | 学术研究 |
| **Deep Learning 加速** | CNN/GAN/Diffusion Model 代理模型 | 推理速度快 | 需要大量训练数据、泛化性 | 快速预测/辅助 |

#### 推荐分阶段实现

**Phase 1 (MVP)：SIMP + 伴随法**
- 基于 OpenFOAM 的孔隙率方法
- 目标函数：最小化压降 + 最大化热传递（多目标加权）
- 约束：体积分数、最小尺寸（通过滤波半径控制）
- 参考文献：面向发动机再生冷却的流热耦合拓扑优化（基于 OpenFOAM 平台）

**Phase 2：Level Set 方法**
- 参数化水平集方法（Parameterized Level Set）
- 处理稳态 Navier-Stokes 流的拓扑优化
- 清晰的流固界面 → 可直接导出 CAD 几何

**Phase 3：AI 加速代理模型**
- 训练 GAN/Diffusion Model 作为快速生成器
- 用物理仿真数据作为训练集
- 推理速度快 100-1000x → 实时预览/快速迭代

**技术难度：★★★★☆（高）**
- SIMP 实现相对成熟（有大量开源参考代码）
- Level Set 方法需要额外的数值处理（再初始化、速度扩展）
- AI 代理模型需要大量训练数据生成
- 预计开发周期：**3-6 个月**（SIMP MVP），**6-12 个月**（完整系统）

---

### B3. 3D 几何内核

#### 选项对比

| 内核 | 许可证 | Web 支持 | 布尔运算 | 导入导出 | 成熟度 |
|------|--------|----------|----------|----------|--------|
| **OpenCASCADE (OCCT)** | LGPL | ✅ 通过 WebAssembly | ✅ | STEP/IGES/STL/BREP | ★★★★★ |
| **OpenGeometry** | MPL-2.0 | ✅ 原生 Rust+WASM | ✅ | STL/STEP/IFC | ★★★☆☆ (新项目) |
| **CGAL** | LGPL/GPL | 部分 WASM 支持 | ✅ | 多种格式 | ★★★★★ |
| **Parasolid** | 商业 | 有限 | ✅ | 多格式 | ★★★★★ |
| **ACIS** | 商业 | 有限 | ✅ | 多格式 | ★★★★☆ |

#### 推荐方案：OpenCASCADE (通过 OpenCASCADE.js)

**核心能力：**
- B-Rep（边界表示法）精确建模
- 布尔运算（并/交/差）
- NURBS 曲面支持
- STEP/IGES 导入导出 → 与 CAE 工具互操作
- 通过 Emscripten 编译为 WebAssembly → 浏览器端运行
- 已有成熟项目验证：Chili3D、CascadeStudio、ArchiYou

**实现路径：**
```
1. 使用 opencascade.js 作为 WebAssembly 绑定层
2. 服务端使用 OCCT C++ 原生库处理复杂几何
3. 拓扑优化输出 → 等值面提取 → OCCT 生成 B-Rep 实体
4. 支持导出 STEP/STL 供下游 CAD/CAE 使用
5. 浏览器端使用 WASM 版本做轻量编辑和预览
```

**技术难度：★★★☆☆（中等）**
- OCCT 本身非常成熟，文档丰富
- WebAssembly 编译需要 Emscripten 经验
- 从拓扑优化结果到清洁 B-Rep 几何的转换是难点
- 预计开发周期：**2-4 个月**

---

### B4. Web 3D 可视化

#### 选项对比

| 库 | 定位 | 科学可视化 | 性能 | 生态 | 许可证 |
|----|------|-----------|------|------|--------|
| **VTK.js** | 科学可视化专用 | ★★★★★ | ★★★★☆ | ★★★★☆ | BSD |
| **Three.js** | 通用 3D 渲染 | ★★★☆☆ | ★★★★★ | ★★★★★ | MIT |
| **ParaView Web** | 远程渲染 | ★★★★★ | ★★★★★ | ★★★☆☆ | BSD |
| **Kitware trame** | 科学 Web 应用框架 | ★★★★★ | ★★★★☆ | ★★★★☆ | Apache |

#### 推荐方案：VTK.js (主) + Three.js (辅)

**VTK.js 核心优势（科学可视化主力）：**
- 专为科学数据设计：支持 ImageData、PolyData、体渲染
- 内置 CFD 可视化能力：流线、等值面、标量场着色、矢量场
- 管线架构（Pipeline）：数据源 → 滤波器 → 映射器 → 渲染器
- 支持 VTK/ParaView 服务器远程渲染
- 兼容 DICOM、CSV、VTK 格式

**Three.js 辅助（UI/交互层）：**
- 设计空间编辑器 UI
- 制造约束可视化
- 轻量级模型预览

**关键功能实现：**
```
1. 优化结果 3D 展示：等值面提取 + 体渲染（密度场）
2. CFD 场数据可视化：温度场、速度场、压力场着色
3. 流道动画：粒子系统 / 流线追踪
4. 设计空间交互编辑：入口/出口位置、热源分布
5. 多方案对比视图：并排渲染 + 性能指标
```

**技术难度：★★★☆☆（中等）**
- VTK.js 有完善的文档和示例
- CFD 数据的高效 Web 渲染需要优化（LOD、数据压缩）
- 预计开发周期：**2-3 个月**

---

### B5. 云基础设施

#### 架构设计

```
┌─────────────────────────────────────────────────┐
│                   Frontend (React + VTK.js)      │
│   设计编辑器 │ 3D查看器 │ 项目管理 │ 协作功能    │
└──────────────────────┬──────────────────────────┘
                       │ REST API / WebSocket
┌──────────────────────┴──────────────────────────┐
│              Backend (FastAPI + Celery)           │
│   用户管理 │ 项目管理 │ 任务调度 │ 文件管理     │
└──────┬───────────┬───────────┬──────────────────┘
       │           │           │
┌──────┴──┐  ┌─────┴────┐  ┌──┴─────────────────┐
│ PostgreSQL│  │MinIO/S3  │  │  HPC Compute Nodes  │
│ 元数据    │  │文件存储   │  │  OpenFOAM Workers   │
│ 用户/项目 │  │模型/结果  │  │  (K8s auto-scaling) │
└─────────┘  └──────────┘  └────────────────────┘
```

#### 关键技术组件

| 组件 | 技术 | 用途 |
|------|------|------|
| **API Gateway** | Nginx / Traefik | 反向代理、SSL、限流 |
| **应用服务器** | FastAPI (Python) | 业务逻辑、API 端点 |
| **任务队列** | Celery + Redis | 异步管理 CFD 计算任务 |
| **计算节点** | K8s + HPC EC2 (c5n.18xlarge / hpc6a) | 弹性伸缩的 OpenFOAM 求解 |
| **对象存储** | AWS S3 / MinIO | 模型文件、仿真结果、VTK 数据 |
| **数据库** | PostgreSQL | 用户、项目、设计参数、性能指标 |
| **实时通信** | WebSocket (Socket.IO) | 计算进度推送、协作编辑 |
| **认证** | OAuth 2.0 + JWT | 多设备登录、团队权限 |
| **CDN** | CloudFront / CloudFlare | 静态资源加速 |

**技术难度：★★★☆☆（中等）**
- 标准 Web 后端架构
- HPC 集群管理需要 DevOps 经验
- 预计开发周期：**2-4 个月**（MVP 用 Docker Compose）

---

### B6. 前端框架

#### 推荐：React + TypeScript + Zustand + Vite

**核心页面：**

| 页面 | 功能 | 关键组件 |
|------|------|----------|
| **设计工作台** | 参数输入 + 3D 预览 + 优化控制 | VTK.js Viewer, 参数面板, 进度条 |
| **项目管理** | 项目列表、团队、分享 | CRUD 表格, 权限管理 |
| **结果分析** | 性能对比、场数据可视化 | 图表 (Recharts), 3D 场渲染 |
| **设计库** | 保存/复用设计模板 | 搜索、分类、预览 |
| **插件市场** | CAE 工具集成 | API 管理 |

**技术栈明细：**
- React 18 + TypeScript
- Vite (构建)
- Zustand (状态管理, 比 Redux 轻量)
- React Query (服务端状态)
- VTK.js + @kitware/vtk.js
- Three.js + @react-three/fiber (辅助 3D)
- TailwindCSS + shadcn/ui
- Socket.IO Client (实时通信)

**技术难度：★★★☆☆（中等）**

---

### B7. 后端框架

#### 推荐：Python FastAPI + Celery + OpenFOAM 微服务

**API 架构：**

```
/api/v1/
├── /auth          # 认证 (JWT)
├── /projects      # 项目 CRUD
├── /designs       # 设计管理
│   ├── POST /create      # 创建设计
│   ├── POST /optimize    # 启动拓扑优化
│   ├── GET  /status/{id} # 查询优化状态
│   └── GET  /result/{id} # 获取优化结果 (VTK data)
├── /simulation    # CFD 仿真
│   ├── POST /run         # 提交 CFD 计算
│   └── GET  /fields/{id} # 获取场数据
├── /geometry      # 几何处理
│   ├── POST /export      # 导出 STEP/STL
│   └── POST /import      # 导入 CAD 模型
├── /materials     # 材料数据库
├── /constraints   # 制造约束配置
└── /teams         # 团队协作
```

**核心服务模块：**
1. **优化引擎服务**：封装 OpenFOAM + 优化算法，容器化部署
2. **几何处理服务**：OpenCASCADE 处理几何导入/导出/修复
3. **数据管理服务**：项目、设计版本、性能指标存储
4. **计算调度服务**：管理 HPC 任务队列，支持优先级和抢占

**技术难度：★★★☆☆（中等）**

---

## C. 技术难度总评

| 模块 | 难度 | 关键挑战 | 所需人才 | 预估工期 |
|------|------|----------|----------|----------|
| **CFD 求解器 + 热-流耦合** | ★★★★★ | 伴随方程推导、收敛性、变物性处理 | CFD 工程师 (PhD 优先) | 6-12 月 |
| **拓扑优化算法 (SIMP)** | ★★★★☆ | 灰度消除、多目标平衡、制造约束嵌入 | 优化算法工程师 | 3-6 月 |
| **拓扑优化算法 (Level Set)** | ★★★★★ | 界面追踪、速度扩展、再初始化 | 优化算法工程师 | 6-12 月 |
| **几何内核集成** | ★★★☆☆ | WASM 编译、优化结果→B-Rep 转换 | C++ / CAD 工程师 | 2-4 月 |
| **Web 3D 可视化** | ★★★☆☆ | 大数据量渲染性能、交互编辑 | 前端 3D 工程师 | 2-3 月 |
| **云平台后端** | ★★★☆☆ | HPC 集群管理、弹性伸缩 | 后端 + DevOps | 2-4 月 |
| **前端应用** | ★★★☆☆ | 复杂交互状态管理 | 前端工程师 | 3-4 月 |
| **制造约束系统** | ★★★★☆ | 工艺约束数学建模（冲压/CNC/蚀刻/3D打印） | 制造工艺 + 算法 | 3-6 月 |
| **AI 代理模型** | ★★★★☆ | 数据生成、模型训练、泛化性 | ML 工程师 | 6-12 月 |
| **CAE 插件集成** | ★★★☆☆ | Ansys API 对接、数据格式转换 | CAE 工程师 | 2-4 月 |

---

## D. 关键技术挑战与风险

### D1. 核心算法风险（最高风险）

| 风险 | 严重度 | 描述 | 缓解策略 |
|------|--------|------|----------|
| 流-热耦合拓扑优化不收敛 | 🔴 极高 | 多物理场耦合导致数值不稳定 | 从 2D 层流开始验证，逐步扩展到 3D 湍流 |
| 灰度区域过多 | 🟠 高 | SIMP 产生大量中间密度，无法制造 | Helmholtz 滤波 + Heaviside 投影 |
| 制造约束难以嵌入 | 🟠 高 | 冲压方向、最小壁厚等约束与优化冲突 | 采用投影/过滤方法嵌入约束 |
| 3D 大规模计算太慢 | 🟠 高 | 高分辨率 3D 优化需要大量计算资源 | GPU 加速、多分辨率策略、AI 代理预筛选 |

### D2. 工程风险

| 风险 | 严重度 | 描述 | 缓解策略 |
|------|--------|------|----------|
| 缺乏 CFD/优化人才 | 🔴 极高 | 跨学科人才稀缺 | 与高校合作、招募博士生 |
| 几何转换质量差 | 🟠 高 | 拓扑优化结果→可制造 CAD 模型有损 | 投入几何后处理算法研发 |
| Web 3D 性能瓶颈 | 🟡 中 | 大规模体数据浏览器渲染卡顿 | LOD、数据降采样、服务端渲染 |
| HPC 成本失控 | 🟠 高 | 大量 CFD 计算费用高 | 弹性伸缩 + 预算限制 + AI 代理替代 |

### D3. 商业风险

| 风险 | 严重度 | 描述 | 缓解策略 |
|------|--------|------|----------|
| 与 ToffeeX 性能差距大 | 🟠 高 | 初期算法精度不如成熟产品 | 聚焦特定垂直场景，做到最好 |
| 用户获取困难 | 🟡 中 | CAE 用户习惯难改变 | 免费试用 + Ansys 插件策略 |
| 知识产权风险 | 🟡 中 | 算法专利规避 | 基于开源学术论文实现 |

---

## E. 分阶段实施计划

### Phase 0：基础设施搭建（月 1-2）

```
□ 搭建开发环境 (Docker, CI/CD)
□ OpenFOAM 编译部署 (本地 + 云 HPC)
□ 基础 FastAPI 后端框架
□ React + VTK.js 前端脚手架
□ PostgreSQL + MinIO 部署
□ 用户认证系统 (JWT)
```

**里程碑：团队可以登录 Web 平台，提交简单的 CFD 计算任务**

### Phase 1：2D MVP — 冷板流道优化（月 2-5）

```
□ 实现 2D SIMP 流体拓扑优化 (基于 OpenFOAM adjointShapeOptimizationFoam)
□ 最小化压降为单一目标函数
□ 体积分数约束
□ Helmholtz 密度滤波
□ MMA 优化器集成
□ 2D 热-流耦合扩展 (加入温度场)
□ Web UI: 2D 设计空间编辑器 (入口/出口/热源设置)
□ Web UI: 2D 优化结果可视化 (密度场 + 速度场)
□ 导出 2D 轮廓为 SVG/DXF
```

**里程碑：用户可以在 Web 上定义 2D 冷板问题，自动生成优化流道布局**

### Phase 2：3D 核心能力（月 5-9）

```
□ 扩展到 3D 拓扑优化
□ 多目标优化：最小化压降 + 最大化热传递 + 温度均匀性
□ 制造约束嵌入 (3D 打印最小壁厚、拔模方向)
□ 3D Web 可视化 (VTK.js 体渲染 + 等值面)
□ OpenCASCADE 几何转换：优化结果 → B-Rep 实体
□ STEP/STL 导出
□ 项目管理系统 (保存/加载/分享设计)
```

**里程碑：用户可以完成完整的 3D 冷板设计流程，导出可制造的几何模型**

### Phase 3：多工艺 + 协作（月 9-13）

```
□ 制造工艺约束扩展：冲压、CNC、化学蚀刻
□ Level Set 方法实现 (清晰边界)
□ 换热器设计支持 (多流道、翅片结构)
□ 歧管设计支持 (多入口/出口)
□ 团队协作功能 (共享项目、评审、评论)
□ 材料数据库 (铝合金、铜、不锈钢等)
□ 参数化设计模板 (常见冷板/换热器规格)
```

**里程碑：支持多种热流体组件类型和制造工艺**

### Phase 4：AI 加速 + 插件生态（月 13-18）

```
□ AI 代理模型训练 (基于 Phase 1-3 积累的数据)
□ 实时设计预览 (AI 生成 + 物理精修)
□ Ansys Discovery 插件 (双向数据同步)
□ API 开放平台 (第三方开发者)
□ 性能基准测试套件
□ 移动端适配 (iPad 查看/轻量编辑)
□ 企业级功能 (SSO、审计日志、私有部署)
```

**里程碑：具备与 ToffeeX 竞争的核心能力**

### Phase 5：持续优化（月 18+）

```
□ GPU 加速求解器 (CUDA / OpenCL)
□ 瞬态热分析
□ 多相流支持
□ 不确定性量化 (UQ)
□ 联邦学习 / 数据隐私保护
□ 拓扑优化 + 点阵结构混合设计 (TPMS)
```

---

## F. 开源生态加速方案

### F1. 核心开源项目

| 项目 | 用途 | GitHub Stars | 推荐度 |
|------|------|-------------|--------|
| [OpenFOAM](https://www.openfoam.com/) | CFD 求解器 | - | ★★★★★ 必用 |
| [DAFoam](https://github.com/mdolab/dafoam) | 多学科离散伴随优化 | ~200 | ★★★★★ 强烈推荐 |
| [pyTop](https://github.com/) | 轻量级 Python 拓扑优化 | - | ★★★★☆ MVP 参考 |
| [OpenMDAO](https://github.com/OpenMDAO/OpenMDAO) | 多学科优化框架 (NASA) | ~600 | ★★★★☆ |
| [FEniCS + Dolfin-Adjoint](https://fenicsproject.org/) | FEM + 自动伴随 | - | ★★★★☆ 学术验证 |
| [ARL_Topologies](https://github.com/) | 可扩展拓扑优化框架 | - | ★★★★☆ |
| [TopOpt (DTU)](https://www.topopt.dtu.dk/) | 经典拓扑优化代码 (99行/88行) | - | ★★★★☆ 教学参考 |
| [OpenTM](https://github.com/quanyuchen2000/OPENTM) | GPU 热微结构优化 | - | ★★★☆☆ 参考 |
| [ToOptiX](https://github.com/) | 多物理场拓扑优化 | - | ★★★☆☆ |

### F2. 几何与可视化

| 项目 | 用途 | 推荐度 |
|------|------|--------|
| [OpenCASCADE.js](https://github.com/nickcernean/opencascade.js) | 浏览器端 CAD 内核 (WASM) | ★★★★★ 必用 |
| [VTK.js](https://github.com/Kitware/vtk-js) | Web 科学 3D 可视化 | ★★★★★ 必用 |
| [Three.js](https://github.com/mrdoob/three.js) | 通用 Web 3D 渲染 | ★★★★☆ 辅助 |
| [Chili3D](https://github.com/nickcernean/chili3d) | 浏览器 CAD 应用参考 | ★★★☆☆ 参考架构 |
| [OpenGeometry](https://github.com/) | Rust+WASM CAD 内核 | ★★★☆☆ 未来备选 |
| [Gmsh](https://gmsh.info/) | 开源网格生成器 | ★★★★★ 必用 |
| [Salome](https://www.salome-platform.org/) | 前后处理平台 | ★★★☆☆ |
| [trame (Kitware)](https://github.com/Kitware/trame) | 科学 Web 应用框架 | ★★★★☆ |

### F3. 云平台与工具链

| 项目 | 用途 |
|------|------|
| [FastAPI](https://fastapi.tiangolo.com/) | Python 后端框架 |
| [Celery](https://docs.celeryq.dev/) | 分布式任务队列 |
| [MinIO](https://min.io/) | S3 兼容对象存储 |
| [Traefik](https://traefik.io/) | 反向代理 / 负载均衡 |
| [Grafana](https://grafana.com/) | 监控与告警 |
| [Socket.IO](https://socket.io/) | 实时双向通信 |

---

## G. 团队配置建议

### MVP 阶段（5-8 人，12 个月）

| 角色 | 人数 | 核心要求 |
|------|------|----------|
| **CFD/优化算法工程师** | 2 | OpenFOAM 经验 + 拓扑优化理论 (PhD 优先) |
| **后端工程师** | 1-2 | Python/FastAPI + 云服务 |
| **前端 3D 工程师** | 1 | React + VTK.js/Three.js |
| **C++/几何工程师** | 1 | OpenCASCADE + WebAssembly |
| **DevOps** | 0.5 (兼职) | K8s + HPC 集群管理 |
| **产品/项目经理** | 0.5 | CAE 行业经验 |

### 扩展阶段（12-18 人）

增加：ML 工程师 (1)、制造工艺专家 (1)、QA (1)、更多前端 (1)

---

## H. 预算估算

### MVP 阶段（12 个月）

| 项目 | 月费用 | 年费用 |
|------|--------|--------|
| 人力成本 (5-8人) | ¥200K-400K | ¥2.4M-4.8M |
| 云 HPC 计算 | ¥10K-50K | ¥120K-600K |
| 云基础设施 | ¥5K-15K | ¥60K-180K |
| 软件许可 (如有) | ¥0-20K | ¥0-240K |
| **总计** | | **¥2.6M-5.8M** |

---

## I. 与 ToffeeX 功能对标

| ToffeeX 功能 | 实现难度 | 对应阶段 | 我们的方案 |
|-------------|----------|----------|-----------|
| 流体拓扑优化 | ★★★★★ | Phase 1-2 | OpenFOAM + SIMP + 伴随法 |
| 冷板设计 | ★★★★☆ | Phase 2 | 2D→3D 渐进实现 |
| 换热器设计 | ★★★★☆ | Phase 3 | 多流道 + 翅片支持 |
| 歧管设计 | ★★★★☆ | Phase 3 | 多入口/出口拓扑 |
| 制造约束 (3D 打印) | ★★★★☆ | Phase 2-3 | 最小壁厚/拔模方向约束 |
| 制造约束 (冲压/CNC) | ★★★★★ | Phase 3 | 工艺特定投影约束 |
| 云端协作 | ★★★☆☆ | Phase 2-3 | Web 平台 + WebSocket |
| 3D 可视化 | ★★★☆☆ | Phase 1-2 | VTK.js + Three.js |
| STEP/STL 导出 | ★★★☆☆ | Phase 2 | OpenCASCADE |
| Ansys 插件 | ★★★☆☆ | Phase 4 | Ansys PyAnsys SDK |
| 40% 热性能提升 | 待验证 | Phase 2+ | 需大量实验验证 |
| AI 生成式设计 | ★★★★☆ | Phase 4 | GAN/Diffusion + 物理精修 |

---

## J. 快速启动建议

### 立即可做的事

1. **搭建 OpenFOAM 环境** → 运行 adjointShapeOptimizationFoam 的 pitzDaily 教程
2. **研读 DAFoam 文档** → 评估是否作为主要优化框架
3. **复现 TopOpt 99 行代码** → 理解 SIMP 核心算法
4. **VTK.js Hello World** → 在浏览器中渲染第一个 3D 标量场
5. **OpenCASCADE.js 试用** → 在浏览器中创建/布尔运算几何体
6. **阅读关键论文**：
   - "面向发动机再生冷却的流热耦合拓扑优化" (OpenFOAM 实现)
   - "DAFoam: An Open-Source Adjoint Framework for MDO with OpenFOAM"
   - "Topology Optimization for Steady-State Navier-Stokes Based on Parameterized Level Set"
   - "Multi-objective topology optimization of liquid-cooled plate structures"

### 技术验证优先级

```
1. [最高] OpenFOAM 2D 流体拓扑优化能否收敛？
2. [最高] 热-流耦合优化能否产出合理的冷板流道？
3. [高]   优化结果能否自动转换为清洁的 3D 几何？
4. [高]   VTK.js 能否流畅渲染 100 万单元的体数据？
5. [中]   WebAssembly 版 OpenCASCADE 性能是否满足交互需求？
```

---

*本文档基于 2026 年 7 月技术调研编写，建议每季度更新一次。*
