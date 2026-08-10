# BlotGuard-AI 后端

本目录已经包含一套可运行的蛋白印迹 AI 生成风险检测后端。系统以
Flask 为 HTTP 边界，以 SQLAlchemy 保存任务元数据，以任务隔离目录保存上传
文件、提取图片和报告，并通过现有 LoRA-SAM 研究代码执行整图检测。

## 已实现

- JPG、JPEG、JFIF、PNG、TIFF、PDF、DOCX 上传。
- 文件大小、扩展名、文件签名、图片尺寸和 DOCX 解压规模校验。
- PDF 内嵌图片和 DOCX 媒体图片提取。
- 持久化任务状态和逐图检测结果。
- 真实 PyTorch 检测适配器和显式开发 mock。
- 中文 PDF 报告。
- 不透明 artifact 下载地址，不暴露本机文件路径。
- 统一 JSON 错误格式和 `X-Request-ID`。
- SQLite 本地开发及 MySQL 部署配置。
- Flask、Gunicorn、Docker Compose 和 NGINX 配置。
- OpenAPI 3.1 接口文档和端到端测试。
- 前端 v0.1 草案兼容接口：`/api/auth/login`、`/api/tasks/upload`、
  `/api/tasks/<task_id>`、`/api/tasks/<task_id>/result`、
  `/api/tasks/<task_id>/report`。

定位模型目前默认关闭。现有论文中的蛋白印迹模型是整图二分类模型，仓库中的
1024 定位权重来源和业务语义仍需模型负责人确认，不能直接将其掩膜解释为
“AI 生成区域”。

## 目录

```text
backend/blotguard/
  api/                 Flask 路由
  core/                配置和错误类型
  domain/              稳定结果契约
  inference/           PyTorch 检测适配器和模型生命周期
  persistence/         SQLAlchemy 数据模型和仓储
  services/            上传、解析、任务、报告和文件存储
backend/tests/          后端测试
configs/default.yaml   默认运行配置
deploy/nginx.conf       NGINX 反向代理
docs/                   架构、API 和模型契约
models/                 权重放置说明
scripts/                开发启动和模型校验
var/                    本地任务文件和 SQLite 数据库，运行时生成
```

## 快速启动

Python 版本统一为 3.10。

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

先使用开发 mock 验证 Web 全链路：

```bash
export BLOTGUARD_INFERENCE_MODE=mock
export BLOTGUARD_EXECUTION_MODE=inline
flask --app backend.blotguard:create_app run --debug
```

若 macOS 的 5000 端口被系统占用：

```bash
BLOTGUARD_PORT=5001 python scripts/run_dev.py
```

访问：

```text
GET http://127.0.0.1:5000/api/v1/health
GET http://127.0.0.1:5000/api/v1/health/ready
```

上传样例：

```bash
curl -F "file=@sample_data/western_blots_dataset/real/real_img_00000.png" \
  http://127.0.0.1:5000/api/v1/analyses
```

返回的 `task_id` 用于查询：

```bash
curl http://127.0.0.1:5000/api/v1/analyses/<task_id>
curl -OJ http://127.0.0.1:5000/api/v1/analyses/<task_id>/report
```

## 启用真实模型

安装模型运行依赖：

```bash
pip install -r requirements-model.txt
```

将 SAM ViT-B 基础权重放到：

```text
models/weights/sam_vit_b_01ec64.pth
```

当前 detector LoRA 权重来自材料目录中的全 12 层 `lorasam_blots20`：

```text
/Users/jamelee/graduate/project/sam_lora_aigc_detect/Ablation/lorasam_blots20/
  rank8-img_size512-vit_b-best_f1.pth
```

复制后固定为：

```text
models/weights/detector/rank8-full12-img_size512-vit_b-blots20-best_f1.pth
```

校验：

```bash
python scripts/verify_model_assets.py
```

三项均为 `OK` 后启动真实推理：

```bash
export BLOTGUARD_INFERENCE_MODE=real
export BLOTGUARD_DEVICE=auto
gunicorn --workers 1 --threads 2 --bind 0.0.0.0:5000 wsgi:app
```

GPU 部署时每张 GPU 建议只启动一个模型进程，避免每个 worker 重复加载
SAM 权重。正式并发扩展应将分析执行器替换为 Redis/Celery GPU worker，
HTTP API 和任务契约无需改变。

PDF 报告会自动寻找 macOS 的 Arial Unicode/Hiragino 或 Linux 的 Noto CJK。
自定义字体可设置 `BLOTGUARD_REPORT_FONT`，Docker 镜像已安装 Noto CJK。

## 数据库

本地默认使用：

```text
sqlite:///var/blotguard.db
```

切换 MySQL：

```bash
export BLOTGUARD_DATABASE_URL='mysql+pymysql://blotguard:blotguard@127.0.0.1:3306/blotguard'
```

图片和报告不存数据库，而是保存在 `var/tasks/<task_id>/`。MongoDB 当前没有
独立数据职责，因此未引入；如指导老师要求使用，应先明确它保存的唯一数据类型，
避免与 MySQL 重复存储。

## 测试

```bash
pytest
```

测试使用显式 mock，只验证上传、解析、状态、数据库、报告和下载链路。真实模型
上线前还必须增加由模型负责人确认的黄金样本回归测试。

使用真实样例运行完整 smoke：

```bash
python scripts/smoke_api.py --mode mock
```

## 关键文档

- `docs/backend-architecture.md`：系统流程、模块边界和扩展路径。
- `docs/api-contract.md`：接口、状态和错误约定。
- `docs/model-contract.md`：当前已知模型参数和待确认事项。
- `docs/detector-data-splits.md`：Detector 原始划分与新冻结测试集。
- `docs/detector-calibration.md`：Calibration、阈值与五级风险诊断结果。
- `docs/openapi.yaml`：前后端共同使用的机器可读契约。
