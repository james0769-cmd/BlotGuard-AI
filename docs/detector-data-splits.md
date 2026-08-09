# Detector 冻结数据划分

## 状态

2026-08-09 从本地完整 Western blot 数据集建立新的 calibration、test 和 reserve
清单。原始图片没有被移动或修改。该 test 是“从本次冻结后不再参与开发”的新
holdout，不能追溯证明其中图片从未被历史脚本查看过。

原始 `lorasam_blots20` 的 train/val 清单已找回：

- `face_blots_20_train_nondomain.txt`：23,099 张。
- `face_blots_20_val_nondomain.txt`：5,774 张。
- 两份清单无路径或文件名重叠，文件均存在。
- 当前 `best_f1` 与 `epoch16` checkpoint 完全相同；epoch16 文件名中的准确率
  `0.9996536196744025` 等于 `5772/5774`，与 val 数量一致。

## 新划分

| 集合 | Real | StyleGAN2-ADA | CycleGAN | Pix2Pix | DDPM | 总数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Calibration | 500 | 500 | 500 | 500 | 500 | 2,500 |
| Test | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 5,000 |
| Reserve | 6,560 | 387 | 387 | 387 | 387 | 8,108 |
| Excluded | — | — | — | — | — | 22,592 |

Excluded 是保守隔离集合，包含历史 train/val、25 张黄金回归、500 张候选审计、
完全重复内容，以及与冻结集合或历史集合感知哈希距离过近的 family。不同排除原因
可能作用于同一 family，因此元数据中的原因计数不能直接相加得到排除图片数。

## 防泄漏规则

- 排除匹配使用图片 SHA-256，不依赖文件名。
- 文件名末尾相同数字编号的五类图片绑定为同一个 `family_id`。
- 感知哈希使用 32×32 灰度图 DCT 的 64-bit hash，最大汉明距离为 4。
- Calibration 与 test 不存在距离不超过 4 的感知哈希冲突。
- Calibration 和 test 各自内部不存在重复 SHA-256，同一图片不会重复计权。
- Reserve 与 calibration/test 不存在距离不超过 4 的感知哈希冲突。
- 四份清单完整覆盖 38,200 张源图片，每个路径只出现一次。
- 每份 manifest、历史清单和已使用清单的 SHA-256 均记录在元数据中。

## 文件

```text
sample_data/western_blots_dataset/splits/
  detector_calibration_manifest.csv
  detector_test_manifest.csv
  detector_reserve_manifest.csv
  detector_excluded_manifest.csv
  detector_split_metadata.json
```

## 使用限制

1. Calibration 只用于分数校准、二分类阈值和五级风险分界点选择。
2. Test 在模型、预处理和所有阈值冻结前不得运行。
3. Test 只做一次最终评估，不得根据结果继续选择 checkpoint 或阈值。
4. Reserve 可供未来模型开发；当前 test 不得加入后续训练。
5. 当前 25 张黄金样本继续只做代码回归，500 张审计集继续只做候选比较。

## 复现与校验

```bash
python scripts/build_detector_splits.py \
  --dataset-root /path/to/western_blots_dataset \
  --face-split-root /path/to/face_blots_20 \
  --exclude-manifest 'sample_data/western_blots_dataset/sample_manifest.csv|.' \
  --exclude-manifest 'var/p0_audit_manifest_500.csv|/path/to/western_blots_dataset' \
  --output-dir sample_data/western_blots_dataset/splits \
  --calibration-per-group 500 --test-per-group 1000 \
  --seed blotguard-detector-split-v1 --phash-distance 4

python scripts/verify_detector_splits.py \
  --dataset-root /path/to/western_blots_dataset \
  --split-dir sample_data/western_blots_dataset/splits
```
