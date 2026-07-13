# BlotGuard-AI

BlotGuard-AI 是一个面向蛋白印迹图像的 AI 生成伪造检测系统。本仓库当前提供 Angular + Flask 工程，以及已经接入的真实 Detector 推理链：

- 整图判别：输出图像为 AI 生成的概率和判定结果。
- 伪造定位：模型入口和权重已保留，本阶段默认关闭。

当前阶段包含单图上传检测，不包含用户认证、数据库、PDF 报告或正式部署编排。

## 目录结构

```text
backend/                       Flask API、配置和模型推理适配层
  blotguard/
    api/                       HTTP 路由
    core/                      运行时配置
    inference/                 检测与定位接口
  tests/                       后端测试
frontend/                      Angular 22 前端工作区
configs/default.yaml           默认模型与数据路径
models/                        可跟踪推理源码、权重清单和本地权重目录
deploy/                        部署边界说明
docs/architecture.md           系统架构说明
scripts/                       兼容的模型 smoke 命令
tests/fixtures/                固定 smoke 测试图片
```

历史训练工作区 `sam_lora_aigc_detect/` 和 `segment-anything-main_lora/` 可在本地保留，但不再是系统运行依赖。

## 模型权重

推理源码已经包含在仓库中。每位成员只需将统一版本的三份权重放入 `models/weights/`，目录和文件名见 [models/README.md](models/README.md)。

放置完成后校验：

```bash
python scripts/verify_model_assets.py
```

权重不会提交到 Git，也不会打入开发镜像；Docker Compose 会从本地仓库目录挂载它们。

## 环境准备

项目 Python 环境为 `blotguard-ai`，Python 版本为 3.10。

```bash
conda create -n blotguard-ai python==3.10
conda activate blotguard-ai
pip install -r requirements.txt
```

前端使用 Node.js 26 和 Angular 22：

```bash
cd frontend
npm ci
```

仓库提交 `package-lock.json`，但不提交 `node_modules`。

## 启动开发环境

推荐使用统一的 CPU Docker 开发环境：

```bash
docker compose -f compose.dev.yaml up --build
```

启动后：

- Angular：`http://localhost:4200`
- Flask：`http://localhost:5000`
- 健康检查：`http://localhost:5000/api/v1/health`

也可以使用本机环境分别启动。

在项目根目录启动后端：

```bash
flask --app backend.blotguard:create_app run --debug
```

后端健康检查地址为 `http://127.0.0.1:5000/api/v1/health`。

在另一个终端启动前端：

```bash
cd frontend
npm start
```

前端开发服务器会将 `/api` 请求代理到 Flask 的 `5000` 端口。

## 模型 smoke 测试

检测：

```bash
python scripts/smoke_detect.py \
  --device cpu \
  --image tests/fixtures/western_blot_sample.png
```

定位：

```bash
python scripts/smoke_segment.py \
  --device cpu \
  --image tests/fixtures/western_blot_sample.png \
  --output outputs/smoke_segment_mask.png
```

两个命令保留原有参数和 JSON 输出字段。模型路径和参数默认读取 `configs/default.yaml`，CLI 参数优先级更高。也可以通过环境变量指定其他配置文件：

```bash
BLOTGUARD_CONFIG=/path/to/config.yaml python scripts/smoke_detect.py
```

固定 25 张样例的 Detector 黄金回归结果：

```bash
python scripts/generate_detector_regression.py --device cpu
```

该命令校验每张输入图片的 SHA-256，并生成：

```text
sample_data/western_blots_dataset/detector_golden.csv
sample_data/western_blots_dataset/detector_golden.json
```

## 真实检测接口

启动后端后，通过 multipart form 上传字段 `image`：

```bash
curl -F "image=@tests/fixtures/western_blot_sample.png" \
  http://127.0.0.1:5000/api/v1/detect
```

响应包含 `logit`、`probability_generated`、`prediction`、`threshold`、
`model_version`、`weight_sha256` 和 `device`。Localizer 本阶段关闭，固定返回
`mask_image_url: null` 与 `suspect_regions: []`。

## 测试

安装 Python 依赖后运行后端测试：

```bash
pip install -r requirements.txt
pytest backend/tests
```

安装前端依赖后运行：

```bash
cd frontend
npm test
npm run build
```

更详细的模块边界和后续扩展位置见 [docs/architecture.md](docs/architecture.md)。
