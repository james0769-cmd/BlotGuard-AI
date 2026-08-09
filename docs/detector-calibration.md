# Detector Calibration 结果

## 结论

已在 2,500 张冻结 calibration 图片上完成当前 Detector 的真实推理、五折 family
交叉验证校准、二分类阈值选择和五级边界计算。当前模型未通过预先冻结的质量门槛，
因此结果状态为 `blocked_model_quality`：不修改线上阈值，不启用五级风险，不运行
封存 test。

## 数据和方法

- Calibration：Real、StyleGAN2-ADA、CycleGAN、Pix2Pix、DDPM 各 500 张。
- 模型：`detector-sam-vit-b-lora-r8-all-img512-51265aec`。
- 预处理：直接缩放至 512×512。
- 分组：5-fold `GroupKFold`，相同 `family_id` 不跨折。
- 类别权重：original/generated 各占 50% 权重，避免四种生成器导致 1:4 先验。
- 校准语义：class-balanced calibrated risk，不是真实部署环境发生概率。

## 校准方法比较

| 方法 | Weighted Brier | Weighted log loss | ECE（10 bins） |
| --- | ---: | ---: | ---: |
| 原始 sigmoid | 0.08936 | 0.28293 | 0.06862 |
| Platt | **0.07769** | **0.25750** | **0.02410** |
| Isotonic | 0.07815 | 0.26932 | 0.02790 |

最终诊断性 calibrator 选择 Platt：

```text
calibrated_risk = sigmoid(1.6140798207144604 * raw_logit + 1.0393688179806109)
```

## 二分类阈值

当前正式阈值 `0.5` 在 calibration 上：FPR 2.6%、recall 75.25%、F1 0.8556。

在 `FPR <= 5%` 下最大化 F1，再以 balanced accuracy 破平局，得到诊断性阈值
`0.3781961500644684`：

| 指标 | 结果 |
| --- | ---: |
| Accuracy | 0.8568 |
| Precision | 0.9852 |
| Recall | 0.8335 |
| F1 | 0.9030 |
| FPR | 0.0500 |
| FNR | 0.1665 |
| Balanced accuracy | 0.8918 |

按组结果：

| 组 | 正确/总数 | 对应 rate | 预设门槛 | 结果 |
| --- | ---: | ---: | ---: | --- |
| Real | 475/500 | 95.0% specificity | FPR ≤ 5% | 通过 |
| CycleGAN | 459/500 | 91.8% recall | ≥ 90% | 通过 |
| DDPM | 274/500 | 54.8% recall | ≥ 80% | **失败** |
| Pix2Pix | 436/500 | 87.2% recall | ≥ 90% | **失败** |
| StyleGAN2-ADA | 498/500 | 99.6% recall | ≥ 90% | 通过 |

DDPM recall 的 Wilson 95% 区间约为 50.4%–59.1%，明显低于门槛，不能归因于
抽样波动。

## 五级风险诊断边界

使用 class-balanced calibrated risk 的 `0.10 / 0.30 / 0.70 / 0.90` 作为政策
分界，反算得到原始 sigmoid score 边界：

| 等级 | 原始 score 范围 |
| --- | --- |
| 极低 | `< 0.1186554090` |
| 低 | `0.1186554090–0.2370573707` |
| 中 | `0.2370573707–0.4702857587` |
| 高 | `0.4702857587–0.6720226015` |
| 极高 | `>= 0.6720226015` |

这些边界只用于诊断。因为模型质量门槛失败，`deployable=false`，后端继续返回
`risk_level=null`，前端继续显示“风险分层待模型阈值”。

## 冻结产物

```text
sample_data/western_blots_dataset/splits/detector_calibration_predictions.csv
sample_data/western_blots_dataset/splits/detector_calibration_result.json
```

逐样本预测文件 SHA-256 为
`81dee0400c87154178aabc98ca4ed1f3852e6165cbd0daebd29dec7b4907b811`。

复现：

```bash
python scripts/run_detector_manifest.py \
  --manifest sample_data/western_blots_dataset/splits/detector_calibration_manifest.csv \
  --sample-root /path/to/western_blots_dataset \
  --output sample_data/western_blots_dataset/splits/detector_calibration_predictions.csv \
  --device cpu --batch-size 8

python scripts/calibrate_detector_scores.py \
  --input sample_data/western_blots_dataset/splits/detector_calibration_predictions.csv \
  --output sample_data/western_blots_dataset/splits/detector_calibration_result.json \
  --max-fpr 0.05
```
