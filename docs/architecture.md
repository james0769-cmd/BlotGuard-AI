# BlotGuard-AI 架构

## 当前目标

当前工程将已经验证的蛋白印迹模型推理能力放入稳定边界，并为后续 Web 系统开发提供清晰入口。历史训练代码与实验资产暂不重构，正式应用代码从 `backend/` 和 `frontend/` 开始演进。

## 组件关系

```text
Angular Web
    |
    | /api/v1
    v
Flask API
    |
    v
Inference adapters
    |-- Detector  -> models/source + detector weight
    `-- Localizer -> models/source + localizer weight

Runtime configuration -> configs/default.yaml
```

### Frontend

`frontend/` 是独立的 Angular 22 工作区：

- `src/app/core/` 存放单例服务和跨功能基础能力。
- `src/app/features/` 按业务功能组织页面与组件。
- 当前仅包含首页和后端健康状态检查。
- 开发代理将 `/api` 转发到本地 Flask 服务，暂不引入额外 CORS 配置。

### Backend

`backend/blotguard/` 是 Flask 应用包：

- `create_app()` 是应用工厂。
- `api/` 只负责 HTTP 协议与路由。
- `core/` 负责配置加载。
- `inference/` 封装 PyTorch 模型，不依赖 Flask 请求对象。

HTTP API 使用 `/api/v1` 前缀。当前端点为：

```text
GET /api/v1/health
-> {"status": "ok", "service": "blotguard-api"}

POST /api/v1/detect
multipart field: image
-> 真实 Detector 推理结果
```

### Inference

推理层提供两个稳定入口：

```python
Detector.predict(image_path) -> DetectionResult
Localizer.predict(image_path, output_path) -> LocalizationResult
```

检测模型使用最长边 512、rank 8 LoRA 和 0–5 层适配器；定位模型使用最长边 1024、rank 8 LoRA 和全层适配器。最小推理源码跟踪在 `models/source/`，权重版本记录在 `models/manifest.yaml`，实际路径由 `configs/default.yaml` 管理。本阶段 Detector 启用，Localizer 关闭。

`scripts/smoke_detect.py` 与 `scripts/smoke_segment.py` 是兼容入口，保留原有 CLI 参数和 JSON 输出格式。

## 历史模型资产

以下目录可以继续作为本地训练和实验资产使用：

- `sam_lora_aigc_detect/`
- `segment-anything-main_lora/`

系统运行不再依赖这两个历史目录。它们继续被 Git 忽略，也不会进入 Docker 构建上下文；前后端成员只需要仓库中跟踪的最小推理源码和 `models/weights/` 下的三份统一权重。

## 后续扩展边界

后续功能应在确有需求时加入：

- 上传和文件解析：后端独立 service，并通过 API 暴露任务接口。
- 鉴伪结果页：新增 Angular feature，不扩张首页组件。
- PDF 报告：独立报告 service，不放入模型适配器。
- 身份认证、MySQL、MongoDB：确定数据模型后再引入。
- 异步任务和横向扩容：推理时延与并发需求明确后再设计。
- NGINX、Compose、Kubernetes：在服务数量和部署目标确定后进入 `deploy/`。

这种顺序避免为尚未实现的功能创建空模块或提前固化基础设施方案。
