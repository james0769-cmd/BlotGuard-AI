# 模型契约

## 当前 detector

| 项目 | 当前配置 |
| --- | --- |
| 任务 | 蛋白印迹整图 AI 生成二分类 |
| 标签 | `0=original`，`1=generated` |
| 骨干 | SAM ViT-B |
| 输入 | RGB，512 x 512 |
| LoRA rank | 8 |
| LoRA 层 | 全部 12 层 |
| 预处理 | 直接缩放到正方形，再使用 SAM normalize |
| 输出 | 单个 logit，经 sigmoid 得到未校准风险分数 `score_generated` |
| 阈值 | 0.5 |
| LoRA SHA-256 | `51265aec...53c3e25` |

配置文件当前引用 `Ablation/lorasam_blots20` 权重，与仓库 manifest 一致。该候选在
固定 25 张样本上由 `18/25` 提升至 `23/25`，在本地 500 张分层审计集上由
`304/500` 提升至 `400/500`。审计集缺少原始训练划分证明，只用于候选横向比较，
不能作为无数据泄漏的正式效果结论。

后端调用入口已固定为 `backend/blotguard/inference/detector.py`，模型烟测脚本为
`scripts/smoke_detect.py`。默认批量样本目录为
`sample_data/western_blots_dataset/`，当前包含 25 张联调图：

- `real/`：13 张真实样本。
- `synth/cyclegan/`：3 张合成样本。
- `synth/ddpm/`：3 张合成样本。
- `synth/pix2pix/`：3 张合成样本。
- `synth/stylegan2ada/`：3 张合成样本。

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

1. 审核 2026-08-09 新冻结的 calibration/test 清单及其历史可见性限制。
2. 使用更多 DDPM 样本重新训练；当前冻结候选在 500 张审计集上仅识别
   `37/100` DDPM。
3. 直接拉伸到 512 x 512 是否为正式预处理。
4. 阈值 0.5 是否经过独立验证集确认，风险分数是否做过校准。
5. CPU/GPU 输出允许误差。
6. 定位模型是否针对蛋白印迹 AIGC，掩膜表示什么。

## 表述限制

公共界面和报告使用“AI 生成风险分数”“疑似 AI 生成”“疑似真实”。接口字段
统一使用 `score_generated`，并返回
`score_semantics=uncalibrated_sigmoid_risk_score`。不得把未经校准的 sigmoid
值称为客观概率，也不得仅凭模型输出认定学术不端。

## 已完成的黄金回归

使用固定 25 张样本运行当前冻结候选，结果与
`detector_golden.json` 逐条一致：

- 样本数：25
- logit 最大绝对误差：0
- score 最大绝对误差：0
- prediction 一致率：25/25
- 按真实标签正确：23/25
- 真实图：13/13
- StyleGAN2-ADA：3/3
- CycleGAN：3/3
- Pix2Pix：3/3
- DDPM：1/3

DDPM 仍是 P0 阻塞项。现有 7 个 `best_f1` 候选和 `lorasam_blots20` 全部 36 个
checkpoint 均未在固定样本上超过 DDPM `1/3`，不能通过简单换 checkpoint 完成修复。

P1 评估可靠性修复记录在 `docs/detector-p1-evaluation.md`。候选评估现已输出完整
二分类指标，阈值扫描必须声明数据角色；非独立审计集的结果不会被标记为可用于
修改正式阈值。当前 `0.5` 阈值保持不变。

原始 train/val 和新冻结 calibration/test/reserve 的来源、数量、哈希与使用限制
记录在 `docs/detector-data-splits.md`。新 test 尚未运行。

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
