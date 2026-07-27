# 前端架构文档 - 生命科学图像伪造检测系统

## 技术栈

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| 框架 | Angular | 21.x | Standalone Components 模式（无 NgModule） |
| UI 库 | Angular Material | 21.x | Material Design 3 风格 |
| 图表 | ECharts | 6.x | 自封装 Directive，不依赖 ngx-echarts |
| HTTP | Angular HttpClient | 内置 | RxJS Observable 驱动 |
| 认证 | JWT | - | HttpInterceptor 自动注入 token |
| 样式 | SCSS | - | BEM 命名 + Material 主题变量 |
| 构建 | Angular CLI (esbuild) | 21.x | 开发热重载、生产 Tree-shaking |

## 项目目录结构

```
src/app/
├── core/                          # 全局单例（认证、HTTP、守卫）
│   ├── interceptors/
│   │   └── jwt.interceptor.ts     # 请求自动附加 Authorization header
│   ├── guards/
│   │   └── auth.guard.ts          # 路由守卫，未登录重定向
│   └── services/
│       ├── auth.service.ts        # 登录/登出/token 存取
│       ├── upload.service.ts      # 文件上传（FormData + 进度）
│       ├── detection.service.ts   # 检测结果查询
│       └── report.service.ts      # 报告生成与下载
│
├── shared/                        # 跨模块复用组件/指令/管道
│   ├── components/
│   │   ├── file-dropzone/         # 拖拽上传区域
│   │   └── loading-spinner/       # 全局加载动画
│   ├── directives/
│   │   └── echarts.directive.ts   # ECharts 图表指令封装
│   └── pipes/
│       └── file-size.pipe.ts      # 字节 → 人类可读格式
│
├── features/                      # 业务页面（懒加载）
│   ├── login/                     # 登录页
│   │   └── login.component.ts
│   ├── workspace/                 # 工作台（上传 + 文件列表）
│   │   └── workspace.component.ts
│   └── detection-detail/          # 鉴伪详情（核心页面）
│       ├── detection-detail.component.ts
│       ├── components/
│       │   ├── canvas-viewer/     # 双图对比画布（缩放/平移/掩码）
│       │   ├── forensic-toolbar/  # 法医工具箱（亮度/对比度）
│       │   ├── suspect-list/      # 可疑区域列表
│       │   └── probability-chart/ # AI 概率分布图
│       └── detection-detail.routes.ts
│
├── app.ts                         # 根组件
├── app.routes.ts                  # 顶层路由（懒加载入口）
└── app.config.ts                  # 应用配置（providers）
```

## 架构设计原则

### 1. Standalone Components（Angular 21 推荐模式）
- 不使用传统 NgModule，每个组件通过 `imports` 声明自己的依赖
- 路由使用 `loadComponent` 懒加载，减少首屏体积

### 2. 分层架构
```
[视图层 Component] → [服务层 Service] → [HTTP层 HttpClient] → [Flask API]
```
- **Component**：只负责渲染和用户交互
- **Service**：封装业务逻辑和 HTTP 调用
- **Interceptor**：横切关注点（认证 token、错误处理）

### 3. 响应式数据流（RxJS）
- Service 返回 `Observable`，Component 用 `async` 管道消费
- 避免手动 `subscribe`，防止内存泄漏
- 长生命周期订阅使用 `takeUntilDestroyed()` (Angular 21 内置)

### 4. 状态管理
- 本项目数据流简单，不引入 NgRx/Signal Store
- 使用 Angular Signals（21.x 稳定特性）管理组件局部状态
- 跨组件通信通过 Service 中的 `signal()` / `BehaviorSubject`

## 关键技术方案

### 跨域处理（开发环境）
- `proxy.conf.json` 将 `/api/*` 转发到 Flask `http://localhost:5000`
- 生产环境通过 Nginx 反向代理，无需前端处理

### 双图画布交互
- 方案：CSS `transform` + 鼠标/触摸事件
- 左右两图共享同一套 `{ scale, translateX, translateY }` 状态
- 掩码叠加：后端返回 Base64 mask → `<canvas>` 以 `globalCompositeOperation` 混合

### JWT 认证流程
```
登录 → 后端返回 token → 存入 localStorage
↓
后续请求 → Interceptor 自动读取 token → 加到 Authorization: Bearer xxx
↓
token 过期 → 后端返回 401 → Interceptor 捕获 → 跳转登录页
```

### 文件上传
- 使用 `HttpRequest` + `reportProgress: true` 获取实时进度
- 支持拖拽(DragEvent) 和 点击选择 两种方式
- 前端不解析文件内容，直接 FormData 发送给后端

### 报告下载
- 请求 `responseType: 'blob'`
- 创建临时 `<a>` + `URL.createObjectURL()` 触发浏览器下载

## 开发规范

### 命名约定
- 文件：`kebab-case`（如 `canvas-viewer.component.ts`）
- 类：`PascalCase`（如 `CanvasViewerComponent`）
- 服务：`camelCase` 方法名（如 `getDetectionResult()`）

### Git 分支策略
- `main` - 稳定版本
- `dev` - 开发集成
- `feature/*` - 功能开发分支

### 环境配置
- 开发：`ng serve` + `proxy.conf.json`
- 生产：`ng build` 输出静态文件，Nginx 部署
