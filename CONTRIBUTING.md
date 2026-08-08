# BlotGuard-AI 贡献指南

感谢参与 BlotGuard-AI 开发。本项目正在从模型验证代码演进为完整的蛋白印迹 AI 图像生成伪造检测系统。所有贡献都应保持模型能力、后端业务流程和前端界面之间的边界清晰。

提交代码前，请先阅读：

- [README.md](README.md)：环境、启动和测试命令。
- [docs/architecture.md](docs/architecture.md)：当前架构和模块边界。
- [configs/default.yaml](configs/default.yaml)：默认模型路径和推理参数。

## 1. 基本原则

- 每个分支和 PR 只解决一个明确问题。
- 只修改完成该问题所必需的代码，不顺手重构无关模块。
- 不添加尚未进入当前需求的功能、基础设施或抽象层。
- 公共接口发生变化时，必须同步更新测试和文档。
- 禁止提交模型权重、数据集、运行输出、密钥或个人机器配置。

## 2. 本地环境

### Python

项目统一使用 Python 3.10 和 `blotguard-ai` conda 环境：

```bash
conda create -n blotguard-ai python==3.10
conda activate blotguard-ai
pip install -r requirements-dev.txt
```

新增或升级 Python 依赖时：

1. 先确认标准库或现有依赖无法满足需求。
2. 在 PR 中说明用途和选择理由。
3. 使用明确版本更新 `requirements.txt` 或 `requirements-dev.txt`。
4. 不得在功能 PR 中顺带升级 PyTorch、TorchVision 或其他模型关键依赖。

### Frontend

前端使用 Node.js 26、Angular 22 和 Angular Material：

```bash
cd frontend
npm ci
```

`package-lock.json` 必须与 `package.json` 同步提交。普通功能 PR 不应顺带升级依赖或重新解析整个 lockfile。

## 3. 模型与权重

推理所需源码已经跟踪在 `models/source/`。每位成员只需在本地准备以下权重目录：

```text
models/weights/
├── sam_vit_b_01ec64.pth
├── detector/rank8-full12-img_size512-vit_b-blots20-best_f1.pth
└── localizer/rank8-img_size1024-vit_b-best_f1.pth
```

具体准备方式见 `models/README.md`。放置完成后必须运行：

```bash
python scripts/verify_model_assets.py
```

默认路径和推理参数位于 `configs/default.yaml`。如果确需使用其他路径，请创建不会入库的本地配置：

```bash
cp configs/default.yaml configs/<name>.local.yaml
BLOTGUARD_CONFIG=configs/<name>.local.yaml python scripts/smoke_detect.py
```

注意：

- 不要为了适配个人路径修改 `configs/default.yaml`。
- `*.pth`、`*.pt`、`*.ckpt`、`*.onnx` 等模型文件不得提交到 Git。
- 两个历史模型目录只用于训练与实验，不在普通前后端 PR 中修改、移动或清理。
- 模型版本发生变化时，PR 必须注明权重文件名、SHA-256 和对应推理参数。

## 4. 分支工作流

从最新的 `main` 创建短生命周期分支：

```bash
git switch main
git pull --ff-only
git switch -c feat/backend-analysis-api
```

分支命名格式：

```text
feat/frontend-<功能>
feat/backend-<功能>
feat/inference-<功能>
fix/frontend-<问题>
fix/backend-<问题>
fix/inference-<问题>
test/<范围>-<内容>
docs/<内容>
chore/<内容>
```

示例：

```text
feat/frontend-upload
feat/backend-analysis-api
fix/inference-mask-size
docs/api-contract
```

不要直接向 `main` 推送开发提交。分支应及时同步 `main`，但禁止对他人的共享分支执行强制推送。

## 5. 目录和职责边界

| 范围 | 主要目录 | 约定 |
| --- | --- | --- |
| 模型与环境 | `backend/blotguard/inference/`、`configs/`、`scripts/`、依赖清单 | 模型加载、预处理、推理参数和回归验证 |
| 后端 | `backend/blotguard/api/` 及后续业务服务、领域和存储模块 | HTTP 接口、业务流程、任务和持久化 |
| 前端 | `frontend/` | 页面、交互、状态展示和 API service |
| 部署 | `deploy/` | 经确认的部署配置，不提前添加占位基础设施 |
| 文档 | `docs/`、`README.md` | 架构、接口、环境和使用说明 |

跨职责修改必须邀请对应负责人评审。例如，后端需要改变推理返回结构时，必须由模型负责人确认；前端需要改变 API 字段时，必须由后端负责人确认。

## 6. 后端规范

- 使用 Flask `create_app()` 应用工厂，不创建模块级全局 Flask 应用。
- `api/` 只处理请求解析、响应和状态码，业务流程应放在独立 service 中。
- `inference/` 不依赖 Flask 请求对象，也不处理数据库和 HTTP。
- 不在模块导入阶段加载 checkpoint；模型在实际需要时初始化。
- 公共函数和结果类型使用类型注解。
- API 使用 `/api/v1` 前缀；破坏兼容性的修改不得静默合并。
- API 字段、任务状态或错误格式变化时，先更新契约测试和接口文档。

当前稳定的 Python 推理入口为：

```python
Detector.predict(image_path) -> DetectionResult
Localizer.predict(image_path, output_path) -> LocalizationResult
```

普通后端功能不得绕过这些接口直接导入历史训练脚本。

## 7. 前端规范

- 使用 standalone component、严格 TypeScript 和 Angular Material。
- 功能页面放在 `src/app/features/<feature>/`。
- 全局单例服务放在 `src/app/core/`。
- HTTP 请求封装在 service 中，不直接写在展示组件里。
- 组件使用 `ChangeDetectionStrategy.OnPush`，局部状态优先使用 signals。
- TypeScript 文件使用 kebab-case 文件名、PascalCase 类名、2 空格缩进和单引号。
- 功能样式放在对应组件的 SCSS 中，避免无必要地修改全局样式。
- UI 行为变化必须增加或更新组件测试，并在 PR 中附截图。

## 8. 测试要求

### 后端和配置

```bash
pytest backend/tests
```

新增 API、配置项或结果字段时，必须添加对应测试。

### 前端

```bash
cd frontend
npm test
npm run build
```

### 模型回归

涉及推理代码、模型路径、预处理、依赖或权重时，必须运行：

```bash
python scripts/smoke_detect.py \
  --device cpu \
  --image tests/fixtures/western_blot_sample.png

python scripts/smoke_segment.py \
  --device cpu \
  --image tests/fixtures/western_blot_sample.png \
  --output outputs/smoke_segment_mask.png

shasum -a 256 outputs/smoke_segment_mask.png
```

PR 中应记录改动前后的：

- `logit`、`score_generated`、`score_semantics` 和 `prediction`。
- 掩膜尺寸、`mask_mean` 和 SHA-256。
- 结果是否预期发生变化；如果变化，说明原因和验证依据。

纯前端改动不强制运行真实模型 smoke；改变 API 与推理集成的后端改动需要运行。

## 9. 提交信息

提交信息使用以下格式：

```text
<type>(<scope>): <summary>
```

常用类型：`feat`、`fix`、`refactor`、`test`、`docs`、`chore`。

示例：

```text
feat(frontend): add image upload page
feat(backend): add analysis endpoint
fix(inference): preserve original mask size
test(backend): cover health endpoint
docs: update local setup guide
```

提交信息应描述实际变化，不使用“update”“修改文件”等模糊表述。

## 10. Pull Request 要求

PR 描述必须包含：

- 改动目的与范围。
- 主要实现方式。
- 测试命令和结果。
- 是否改变 API、配置或推理结果。
- 是否新增或升级依赖。
- UI 改动截图（如适用）。
- 模型回归数据（如适用）。

提交 PR 前检查：

- [ ] 分支基于最新 `main`。
- [ ] 没有无关重构或格式化改动。
- [ ] 没有提交权重、数据、输出、密钥或本地配置。
- [ ] 对应测试已通过。
- [ ] 公共接口变化已更新测试和文档。
- [ ] 已邀请受影响模块的负责人评审。

满足上述条件并完成至少一次有效代码评审后，PR 才能合并。
