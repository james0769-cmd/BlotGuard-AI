# 蛋白印迹 AI 检测

这个目录目前保留两条模型主线：

- `sam_lora_aigc_detect/`：基于 SAM image encoder + LoRA + 分类头的 AI 生成/伪造检测。
- `segment-anything-main_lora/`：基于 SAM + LoRA 的篡改区域定位/分割。

当前新增的文件主要用于先把环境搭起来，并做最小 smoke test，确认模型、权重和一张图片的前向推理可以跑通。

## Docker

默认 Dockerfile 使用 CUDA 版 PyTorch 镜像，适合 Linux + NVIDIA GPU：

```bash
docker build -t wb-ai:cu118 .
docker run --rm -it --gpus all \
  -v "$PWD":/workspace \
  -v /Users/jamelee/graduate/data:/data:ro \
  wb-ai:cu118
```

如果只是在 Mac Docker 里做 CPU smoke test，可以改用 CPU 基础镜像并在构建时安装 CPU 版 PyTorch：

```bash
docker build \
  --build-arg BASE_IMAGE=python:3.10-slim \
  --build-arg INSTALL_TORCH=1 \
  -t wb-ai:cpu .
docker run --rm -it \
  -v "$PWD":/workspace \
  -v /Users/jamelee/graduate/data:/data:ro \
  wb-ai:cpu
```

Mac Docker 通常不能使用本机 Apple MPS 或 NVIDIA CUDA，CPU 跑 SAM 会比较慢。

## Smoke Test

进入容器后可以先检查依赖：

```bash
python -c "import torch, cv2, sklearn; print(torch.__version__, torch.cuda.is_available())"
```

分类检测 smoke test：

```bash
python scripts/smoke_detect.py \
  --image /data/western_blots/western_blots_dataset/real/real_img_04818.png
```

定位分割 smoke test：

```bash
python scripts/smoke_segment.py \
  --image /data/western_blots/western_blots_dataset/synth/stylegan2ada/stylegan2ada_img_00001.png \
  --output outputs/smoke_segment_mask.png
```

如果不传 `--image`，脚本会尝试从当前目录的 `data/` 符号链接里找一张 western blot 图片；在 Docker 里更建议显式传 `/data/...` 路径。

## 配置

`configs/paths.example.yaml` 记录了当前默认模型权重和数据路径。后续如果要做后端 API 或批量推理，可以基于这个文件复制出本地配置，例如 `configs/paths.local.yaml`。
