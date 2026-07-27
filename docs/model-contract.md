# 模型契约

## 当前 detector

| 项目 | 当前配置 |
| --- | --- |
| 任务 | 蛋白印迹整图 AI 生成二分类 |
| 标签 | `0=original`，`1=generated` |
| 骨干 | SAM ViT-B |
| 输入 | RGB，512 x 512 |
| LoRA rank | 8 |
| LoRA 层 | 0-5 |
| 预处理 | 直接缩放到正方形，再使用 SAM normalize |
| 输出 | 单个 logit，经 sigmoid 得到风险分数 |
| 阈值 | 0.5 |
| LoRA SHA-256 | `4939e568...e82cad8` |

配置文件当前引用 `Ablation/layer1_5` 权重，与 GitHub 仓库 manifest 一致。

后端调用入口已固定为 `backend/blotguard/inference/detector.py`，模型烟测脚本为
`scripts/smoke_detect.py`。默认批量样本目录为
`sample_data/western_blots_dataset/`，当前包含 25 张联调图：

- `real/`：5 张真实样本。
- `synth/cyclegan/`：5 张合成样本。
- `synth/ddpm/`：5 张合成样本。
- `synth/pix2pix/`：5 张合成样本。
- `synth/stylegan2ada/`：5 张合成样本。

运行方式：

```bash
/Users/zhao/miniforge3/envs/blotguard-backend/bin/python scripts/smoke_detect.py --mode mock
/Users/zhao/miniforge3/envs/blotguard-real/bin/python scripts/verify_model_assets.py
/Users/zhao/miniforge3/envs/blotguard-real/bin/python scripts/smoke_detect.py --mode real --device cpu
```

`mock` 只验证后端调用链和 JSON 输出结构；`real` 会真正调用
`backend.blotguard.inference.detector.Detector`。本项目已在独立的
`blotguard-real` 环境中安装 PyTorch、TorchVision、OpenCV 和模型源码依赖，
并从本地权重压缩包准备了三份权重。

## 上线前必须由模型负责人签字确认

1. 默认权重是否应改为 `lorasam_dadc_blot20`。
2. 论文全 12 层配置与仓库 0-5 层配置为何不同。
3. 直接拉伸到 512 x 512 是否为正式预处理。
4. 阈值 0.5 是否经过验证集确认，风险分数是否做过校准。
5. 25 张联调样本的固定输出和允许误差。
6. 定位模型是否针对蛋白印迹 AIGC，掩膜表示什么。

## 表述限制

公共界面和报告使用“AI 生成风险分数”“疑似 AI 生成”“疑似真实”。不得把
未经校准的 sigmoid 值称为客观概率，也不得仅凭模型输出认定学术不端。

## 已完成的黄金回归

使用 GitHub `main` 中的固定 25 张样本运行真实模型，结果与
`detector_golden.json` 逐条一致：

- 样本数：25
- logit 最大绝对误差：0
- score 最大绝对误差：0
- prediction 一致率：25/25
- 汇总：9 generated，16 original

本地连续编号的 25 张联调样本也已全部完成真实推理，结果保存在被忽略的
`var/real_smoke_25.json`。

## 黄金回归维护

正式模型确认后，应保存：

- 每张固定样本的 logit 和风险分数。
- 模型版本、基础权重及 LoRA 权重 SHA-256。
- CPU/GPU 允许误差。
- 预处理模式和依赖版本。

任何推理代码、依赖、权重或预处理变化都必须重新运行回归。

当前已生成 mock 基线：

```text
sample_data/model_outputs/detector_mock_baseline.json
```

该文件只用于确认 25 张样本可被后端批量调起，不代表真实模型效果。真实基线需要模型负责人
提供同一批样本的正式推理输出。
