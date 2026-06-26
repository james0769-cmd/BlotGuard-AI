# 蛋白印迹 AI 检测

当前阶段目标是先把模型运行环境固定下来，并确认两条模型链路可以完成最小前向推理。

本项目当前保留两条模型主线：

- `sam_lora_aigc_detect/`：基于 SAM image encoder + LoRA + 分类头的 AI 生成/伪造检测。
- `segment-anything-main_lora/`：基于 SAM + LoRA 的篡改区域定位/分割。

## 当前已验证环境

已在 Mac Docker CPU 环境中验证通过：

```text
基础镜像：python:3.10-slim
镜像名：wb-ai:cpu
torch：2.6.0+cpu
torchvision：0.21.0
numpy：1.26.4
opencv-python-headless：4.11.0
CUDA：False
```

Dockerfile 默认使用清华 PyPI 源。之前直接走官方 PyPI 时，`torch`、`opencv-python-headless` 等大文件下载出现过 hash mismatch。

## 构建镜像

在项目根目录执行：

```bash
docker build -t wb-ai:cpu .
```

`.dockerignore` 已排除数据、权重、输出目录和两个大模型代码目录，避免 Docker build context 过大。模型代码和数据在运行容器时通过挂载使用。

## 启动容器

macOS / Linux：

```bash
docker run --rm -it \
  -v "$PWD":/workspace \
  -v /Users/jamelee/graduate/data:/data:ro \
  wb-ai:cpu
```

Windows PowerShell 示例：

```powershell
docker run --rm -it `
  -v ${PWD}:/workspace `
  -v D:\path\to\data:/data:ro `
  wb-ai:cpu
```

团队成员需要把第二个挂载路径替换成自己机器上的数据集目录。容器内统一使用 `/data`。

## 依赖检查

进入容器后执行：

```bash
python -c "import torch, torchvision, cv2, sklearn, numpy; print(torch.__version__, torchvision.__version__, numpy.__version__, cv2.__version__, torch.cuda.is_available())"
```

预期输出类似：

```text
2.6.0+cpu 0.21.0 1.26.4 4.11.0 False
```

## Smoke Test

分类检测 smoke test：

```bash
python scripts/smoke_detect.py \
  --device cpu \
  --image /data/western_blots/western_blots_dataset/real/real_img_04818.png
```

已验证输出示例：

```json
{
  "task": "detect",
  "probability_generated": 0.7050296664237976,
  "prediction": "generated"
}
```

定位分割 smoke test：

```bash
python scripts/smoke_segment.py \
  --device cpu \
  --image /data/western_blots/western_blots_dataset/synth/stylegan2ada/stylegan2ada_img_00001.png \
  --output outputs/smoke_segment_mask.png
```

已验证输出示例：

```json
{
  "task": "segment",
  "mask_shape": [256, 256],
  "mask_mean": 0.071990966796875,
  "output": "outputs/smoke_segment_mask.png"
}
```

输出 mask 会生成到：

```text
outputs/smoke_segment_mask.png
```

## 配置文件

`configs/paths.example.yaml` 是路径配置模板，记录当前默认模型权重、代码目录、输入尺寸和 LoRA 参数。后续批量推理或后端 API 可以基于它复制本地配置：

```text
configs/paths.local.yaml
```

本地配置文件不会提交到 Git。

## Git 协作注意

当前 `.gitignore` 会忽略：

- `data/`
- `outputs/`
- `checkpoints/`
- `*.pth`、`*.pt`、`*.onnx` 等大模型文件
- `sam_lora_aigc_detect/`
- `segment-anything-main_lora/`

这意味着现阶段 GitHub 主要同步 Docker、脚本、配置模板和项目说明。若后续决定把两套模型代码也纳入 GitHub 协作，需要调整 `.gitignore` 中对应规则。

## GPU 环境

当前已验证的是 CPU 开发镜像，适合 Mac / Windows / 普通开发机先跑通流程。

Linux + NVIDIA GPU 服务器环境建议后续单独做 `Dockerfile.gpu` 并验证，不建议直接把本地 CPU 镜像当作训练或正式推理环境。
