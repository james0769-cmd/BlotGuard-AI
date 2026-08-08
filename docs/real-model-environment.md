# 真实模型运行环境

## 环境

已创建 Conda 环境：

```text
/Users/zhao/miniforge3/envs/blotguard-real
```

已安装项目依赖、PyTorch 2.6.0、TorchVision 0.21.0、OpenCV 4.11.0 和
模型源码需要的 `icecream`。

## 权重

本地权重来自：

```text
/Users/zhao/code/蛋白质模型/模型权重.zip
```

解压后的路径：

```text
models/weights/sam_vit_b_01ec64.pth
models/weights/detector/rank8-full12-img_size512-vit_b-blots20-best_f1.pth
models/weights/localizer/rank8-img_size1024-vit_b-best_f1.pth
```

权重目录已写入 `.gitignore`，不会提交到 GitHub。

## 验证和运行

```bash
conda activate blotguard-real
python scripts/verify_model_assets.py
python scripts/smoke_detect.py --mode real --device cpu
```

本机启动真实后端：

```bash
BLOTGUARD_INFERENCE_MODE=real \
BLOTGUARD_DEVICE=cpu \
BLOTGUARD_PORT=5001 \
python scripts/run_dev.py
```

Apple Silicon 可将 `BLOTGUARD_DEVICE` 改为 `mps`，但提交前的黄金回归统一使用
CPU 结果。
