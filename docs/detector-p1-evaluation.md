# Detector P1 评估可靠性修复

## 结论

P1 已补齐可复现的分类指标、阈值扫描和非正方形预处理回归保护。正式阈值继续
冻结为 `0.5`，因为当前 500 张数据只能作为审计集，无法证明与训练集隔离，不能
用于选择线上阈值。

后续已建立无已知泄漏的 calibration，并完成 family 分组交叉验证。诊断性阈值更新
为 `0.3781961500644684`，但模型未通过 DDPM/Pix2Pix 质量门槛，因此正式阈值仍不
变，五级边界不部署。完整结果见 `docs/detector-calibration.md`。

## 完整指标

当前冻结模型在 500 张分层审计集、阈值 `0.5` 下的结果：

| 指标 | 结果 |
| --- | ---: |
| Accuracy | 0.8000 |
| Precision | 0.9902 |
| Recall | 0.7575 |
| F1 | 0.8584 |
| Specificity | 0.9700 |
| FPR | 0.0300 |
| FNR | 0.2425 |
| Balanced accuracy | 0.8638 |

这些数字用于发现回归和比较候选，不作为无数据泄漏的正式模型效果声明。

## 阈值审计

在 FPR 不超过 `5%` 的约束下，审计集上的诊断性最优阈值为
`0.41920268535614014`：F1 `0.8874`、recall `0.8075`、FPR `0.05`。该结果的
`eligible_for_config_change` 固定为 `false`，因此没有改动 `configs/default.yaml`
中的正式阈值。

只有输入被明确标记为 `validation` 时，工具才会把结果标记为可供配置决策；最终
效果仍必须在未参与阈值选择的独立 `test` 集上报告。

## 预处理回归

`stretch` 和 `longest_side` 的尺寸计算已提取为可测试逻辑。当前正式
`stretch` 对任意输入输出 `512×512`；`longest_side` 保持宽高比。测试覆盖了横图、
竖图、四舍五入边界和非法模式，避免后续修改悄悄改变模型输入。

## 复现

```bash
python scripts/analyze_detector_thresholds.py \
  --input var/p0_audit_500_results.json \
  --candidate lorasam_blots20 \
  --preprocess-mode stretch \
  --dataset-role audit \
  --max-fpr 0.05 \
  --output var/p1_threshold_audit.json
```

评估脚本现在统一输出 accuracy、precision、recall、F1、specificity、FPR、FNR、
balanced accuracy、混淆矩阵以及各数据组准确率。
