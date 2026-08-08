# Detector P0 候选评测

## 结论

冻结 `lorasam_blots20` 全 12 层、rank 8、512×512、`stretch` 作为当前默认
Detector。它在固定 25 张样本和本地 500 张分层审计集上均显著优于原
`layer1_5` 权重，同时降低真实图误报。

DDPM 漏检尚未修复完成：新候选在 500 张审计集中识别 `37/100`，仍不足以上线。
P0 只能标记为“部分改善”，剩余工作需要可追溯的数据划分和包含 DDPM 的重新训练。

## 冻结配置

| 项目 | 值 |
| --- | --- |
| 权重来源 | `Ablation/lorasam_blots20/rank8-img_size512-vit_b-best_f1.pth` |
| 系统路径 | `models/weights/detector/rank8-full12-img_size512-vit_b-blots20-best_f1.pth` |
| SHA-256 | `51265aecd96858feeead19cc47f9bd3dc0af3fa7d793582482a9287a153c3e25` |
| 大小 | 2751077 bytes |
| LoRA | rank 8，全部 12 个编码层 |
| 输入 | RGB，直接缩放至 512×512 |
| 判定阈值 | 0.5（仍待独立验证集确认） |
| 版本 | `detector-sam-vit-b-lora-r8-all-img512-51265aec` |

## 固定 25 张样本

| 模型 | 正确 | 真实图 | StyleGAN2-ADA | CycleGAN | Pix2Pix | DDPM | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 原 `layer1_5` | 18/25 | 11/13 | 2/3 | 2/3 | 3/3 | 0/3 | 2 | 5 |
| 冻结 `lorasam_blots20` | 23/25 | 13/13 | 3/3 | 3/3 | 3/3 | 1/3 | 0 | 2 |

`stretch` 与 `longest_side` 在这 25 张正方形样本上输出完全相同，因此本次评测
不能证明两种预处理在非正方形输入上的等价性。

## 500 张分层审计集

审计集从本地完整数据目录等距抽取：100 张真实图，以及 StyleGAN2-ADA、
CycleGAN、Pix2Pix、DDPM 各 100 张。每个样本均记录 SHA-256。由于材料中缺少
原始训练划分清单，无法证明审计图片未参与训练，因此这些结果只用于候选横向比较。

| 模型 | 正确 | 真实图 | StyleGAN2-ADA | CycleGAN | Pix2Pix | DDPM | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 原 `layer1_5` | 304/500 | 89/100 | 94/100 | 59/100 | 61/100 | 1/100 | 11 | 185 |
| 冻结 `lorasam_blots20` | 400/500 | 97/100 | 98/100 | 83/100 | 85/100 | 37/100 | 3 | 97 |

## 已排除方案

- `longest_side`：固定样本均为正方形，无法改善 DDPM。
- `lorasam_dadc_blot20`：固定样本 22/25，DDPM 0/3。
- rank 4、rank 16、后 6 层、`lorasam_blots10`：均不优于冻结候选。
- `lorasam_blots20` 的 36 个 checkpoint：没有任何一个超过 DDPM 1/3。
- 降低阈值：在固定 25 张样本上虽可命中 DDPM 3/3，但会产生 3/13 真实图误报，
  总体正确率从 23/25 降至 22/25，不能作为修复。

## 剩余 P0

1. 找回或重建可追溯的 train/validation/test 清单，保证独立测试集无数据泄漏。
2. 在训练集补充 DDPM，并在独立验证集上重新训练和选择 checkpoint。
3. 在独立测试集报告 accuracy、precision、recall、F1、FPR、FNR 及各生成器指标。
4. 新模型必须同时满足 DDPM 召回提升和真实图误报不恶化，才能替换当前冻结候选。

复现工具：

```bash
python scripts/build_detector_audit_manifest.py --dataset-root <dataset> \
  --samples-per-group 100 --output var/detector_audit_manifest.csv

python scripts/evaluate_detector_candidates.py \
  --manifest var/detector_audit_manifest.csv \
  --sample-root <dataset> \
  --candidate 'name|/path/to/weight.pth|8|all' \
  --preprocess-mode stretch --device cpu
```
