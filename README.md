# BlotGuard-AI

BlotGuard-AI 是一个面向蛋白印迹图像的 AI 生成伪造检测系统。本仓库当前提供可扩展的 Angular + Flask 工程基础，以及两条已经验证的模型推理链：

- 整图判别：输出图像为 AI 生成的概率和判定结果。
- 伪造定位：输出与原图同尺寸的二值掩膜。

当前阶段不包含文件上传、用户认证、数据库、PDF 报告或正式部署编排。

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
deploy/                        部署边界说明
docs/architecture.md           系统架构说明
scripts/                       兼容的模型 smoke 命令
sam_lora_aigc_detect/          历史检测模型目录，本地保留且不入库
segment-anything-main_lora/    历史定位模型目录，本地保留且不入库
```

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
npm install
```

仓库不提交 `node_modules`。首次安装依赖后应提交 npm 生成的 lockfile。

## 启动开发环境

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
  --image sam_lora_aigc_detect/original_image.png
```

定位：

```bash
python scripts/smoke_segment.py \
  --device cpu \
  --image sam_lora_aigc_detect/original_image.png \
  --output outputs/smoke_segment_mask.png
```

两个命令保留原有参数和 JSON 输出字段。模型路径和参数默认读取 `configs/default.yaml`，CLI 参数优先级更高。也可以通过环境变量指定其他配置文件：

```bash
BLOTGUARD_CONFIG=/path/to/config.yaml python scripts/smoke_detect.py
```

## 测试

安装开发依赖后运行后端测试：

```bash
pip install -r requirements-dev.txt
pytest backend/tests
```

安装前端依赖后运行：

```bash
cd frontend
npm test
npm run build
```

更详细的模块边界和后续扩展位置见 [docs/architecture.md](docs/architecture.md)。
