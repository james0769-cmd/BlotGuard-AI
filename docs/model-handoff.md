# BlotGuard-AI 模型交接文档

## 1. 交接范围

本文覆盖阶段开发计划中的模型相关任务，包括模型结构、权重、输入输出、运行环境、推理入口、已完成验证、待补材料和联调边界。前端、后端业务接口、数据库、报告生成和部署不在本文范围内。

## 2. 模型能力

系统当前包含两条基于 SAM ViT-B 和 LoRA 的推理链。

|能力|稳定入口|模型配置|结果|
|---|---|---|---|
|整图检测|`Detector.predict(image_path)`|输入 512 x 512，LoRA rank 8，适配编码器第 0～5 层|AI 生成风险分数和二分类标签|
|伪造定位|`Localizer.predict(image_path, output_path)`|输入最长边 1024，LoRA rank 8，适配全部编码器层|入口保留，本阶段默认关闭|

最小推理源码位于：

- `models/source/segment_anything/`：检测和定位共用的 SAM 推理源码。
- `models/source/classifier/`：整图检测使用的 FCN 分类器。
- `backend/blotguard/inference/`：面向系统调用的检测、定位适配器。

历史训练工作区位于 `/Users/jamelee/graduate/project/`，不是当前系统运行依赖。训练代码、数据集划分和实验记录仍需模型负责人从历史工作区另行确认。

## 3. 模型权重

运行时需要以下三份权重：

|名称|系统内路径|用途|大小（bytes）|SHA-256|
|---|---|---|---:|---|
|SAM ViT-B|`models/weights/sam_vit_b_01ec64.pth`|检测、定位共用的基础权重|375042383|`ec2df62732614e57411cdcf32a23ffdf28910380d03139ee0f4fcbe91eb8c912`|
|Detector LoRA|`models/weights/detector/rank8-img_size512-vit_b-best_f1.pth`|整图 AI 生成检测|2153517|`4939e56854dc4b080327a4b5841fba651f0ea6e812006eb2e9a0b0eaee82cad8`|
|Localizer LoRA|`models/weights/localizer/rank8-img_size1024-vit_b-best_f1.pth`|像素级伪造定位|17500687|`337ef9d06885a30ec52b8aee69dd0d9c223ef71396f16bcbd57cf5df157fe552`|

三份文件已放入上述路径，并于 2026 年 7 月 12 日通过大小和 SHA-256 校验。权重受 Git 忽略规则保护，不应提交到仓库。

校验命令：

```bash
conda run -n blotguard-ai python scripts/verify_model_assets.py
```

预期三项均显示 `OK`。

历史来源：

```text
/Users/jamelee/graduate/project/sam_lora_aigc_detect/pretrained_weights/sam_vit_b_01ec64.pth
/Users/jamelee/graduate/project/sam_lora_aigc_detect/Ablation/layer1_5/rank8-img_size512-vit_b-best_f1.pth
/Users/jamelee/graduate/project/segment-anything-main_lora/western_blot/weight_1024/rank8-img_size1024-vit_b-best_f1.pth
```

检测 checkpoint 包含 12 组 LoRA A/B 参数和 FCN 分类器参数，对应 6 个编码层的 Q、V 适配。定位 checkpoint 包含 24 组 LoRA A/B 参数以及 SAM prompt encoder、mask decoder 参数，对应 12 个编码层的 Q、V 适配。

## 4. 运行环境

项目专用 Conda 环境：

```text
名称：blotguard-ai
路径：/Users/jamelee/dev_tools/miniconda3/envs/blotguard-ai
Python：3.10.0
```

推荐通过环境内 Python 直接运行：

```bash
/Users/jamelee/dev_tools/miniconda3/envs/blotguard-ai/bin/python <script>
```

后端同学不依赖上述本机路径，按仓库锁定依赖重新创建即可：

```bash
conda create -n blotguard-ai python=3.10
conda activate blotguard-ai
pip install -r requirements.txt
```

真实 Detector/Localizer 入口必须安装 `torch`、`torchvision`、`numpy`、`opencv-python-headless`、`PyYAML` 和 `icecream`；HTTP 服务还需要 `Flask`。具体版本以 `requirements.txt` 为准。

环境可以完成两条 CPU 模型推理。本阶段 Detector 的实测数据为：单张 smoke 包含模型加载共 2.43 秒；同一进程连续处理固定 25 张共 11.66 秒。数据来自当前 macOS 机器，仅用于开发估算。

GPU、峰值内存和显存需求尚未测量。Linux 尚未完成一致性验证。现阶段已验证的是 macOS CPU 可运行，不应据此承诺生产性能。

## 5. 输入和预处理

当前稳定入口接收本地图片路径，不直接接收 HTTP 文件对象、Base64 或 NumPy 数组。

```python
Detector.predict(image_path)
Localizer.predict(image_path, output_path)
```

预处理流程：

1. 使用 OpenCV 以彩色模式读取图片。
2. 将 BGR 转为 RGB。
3. 当前 Detector 将图像直接缩放至 512 x 512；是否改为保持宽高比仍待模型负责人确认。
4. 检测模型使用 512，定位模型使用 1024。
5. 调用 SAM `preprocess()` 完成标准化和尺寸补齐。
6. 定位结果经 SAM `postprocess_masks()` 恢复到原图尺寸。

当前未在模型层限制文件扩展名、文件大小、宽高或色彩空间。Web 上传校验应由后端负责，支持范围需在首次真实接口联调时共同确认。

## 6. 输出契约

### 6.1 整图检测

模型产生单个 logit，经 sigmoid 转换为 `score_generated`。该值没有经过概率校准，固定语义为 `uncalibrated_sigmoid_risk_score`，只能解释为 AI 生成风险分数。当前固定阈值为 0.5：大于 0.5 为 `generated`，否则为 `original`。

```json
{
  "task": "detect",
  "image": "tests/fixtures/western_blot_sample.png",
  "device": "cpu",
  "logit": 0.5585181713104248,
  "score_generated": 0.6361096501350403,
  "score_semantics": "uncalibrated_sigmoid_risk_score",
  "prediction": "generated",
  "threshold": 0.5,
  "model_name": "western-blot-aigc-detector",
  "model_version": "detector-sam-vit-b-lora-r8-l0-5-img512-4939e568",
  "weight_sha256": "4939e56854dc4b080327a4b5841fba651f0ea6e812006eb2e9a0b0eaee82cad8",
  "is_mock": false,
  "mask_available": false,
  "mask_image_url": null,
  "localization_message": "当前版本不提供区域定位"
}
```

注意：当前 0.5 是代码判定阈值，尚无验证集阈值分析材料证明它是业务最优阈值。前端和报告可以展示“模型判断”或“AI 生成风险”，不应表述为确定的事实结论。

### 6.2 伪造定位

本阶段 `localizer_enabled = false`。后端固定返回 `mask_available = false`、`mask_image_url = null`、`suspect_regions = []` 和“当前版本不提供区域定位”。以下内容是后续启用时的模型输出说明。

模型输出单通道 mask logits，经 sigmoid 后使用 0.5 阈值二值化：0 表示未标记区域，255 表示模型标记区域。掩膜以 8-bit 灰度 PNG 保存。

```json
{
  "task": "segment",
  "image": "tests/fixtures/western_blot_sample.png",
  "device": "cpu",
  "mask_shape": [256, 256],
  "mask_mean": 0.2121734619140625,
  "output": "outputs/smoke_segment_mask.png"
}
```

`mask_mean` 表示二值掩膜中被标记像素的占比，不是置信度，也不能直接等同于整图 AI 生成风险分数。

## 7. 最小推理与回归基线

单张 smoke 固定样例：

```text
tests/fixtures/western_blot_sample.png
PNG，256×256，8-bit RGB
```

CPU smoke 命令：

```bash
/Users/jamelee/dev_tools/miniconda3/envs/blotguard-ai/bin/python \
  scripts/smoke_detect.py \
  --device cpu \
  --image tests/fixtures/western_blot_sample.png

/Users/jamelee/dev_tools/miniconda3/envs/blotguard-ai/bin/python \
  scripts/smoke_segment.py \
  --device cpu \
  --image tests/fixtures/western_blot_sample.png \
  --output outputs/smoke_segment_mask.png
```

2026 年 7 月 12 日基线结果：

|检查项|基线值|
|---|---|
|检测 logit|0.5585181713104248|
|AI 生成风险分数|0.6361096501350403|
|检测标签|`generated`|
|掩膜尺寸|256×256|
|掩膜标记比例|0.2121734619140625|
|掩膜 SHA-256|`b655d165578753b2317afe14fcb2b5693457924046b840b6c4e7aaa0191a7766`|

以上结果只用于检查代码、依赖和权重是否发生非预期变化，不代表模型准确率或泛化性能。

固定 25 张回归样例位于 `sample_data/western_blots_dataset/`：13 张真实图，以及 StyleGAN2-ADA、CycleGAN、Pix2Pix、DDPM 各 3 张。输入清单和真实 Detector 输出分别位于：

```text
sample_data/western_blots_dataset/sample_manifest.csv
sample_data/western_blots_dataset/detector_golden.csv
sample_data/western_blots_dataset/detector_golden.json
```

重新生成命令：

```bash
python scripts/generate_detector_regression.py --device cpu
```

## 10. 已知限制和待确认问题

- 当前 25 张固定样例仅用于回归，不能据此评价准确率、召回率或泛化能力。
- 两个 `best_f1` 权重的验证集、F1 数值和选择过程未在当前仓库记录。
- 检测与定位均使用固定 0.5 阈值，尚未提供阈值标定证据。
- 检测标签只表达模型判断，不构成科研诚信、法律或事实层面的最终鉴定。
- 定位掩膜是模型标记区域，不保证覆盖所有伪造区域，也可能产生误报。
- 当前实现按单张图片同步推理，尚未验证批处理和并发行为。
- GPU 路径、跨平台一致性、资源占用和性能数据尚未验证。
- ONNX 导出和部署未验证，当前可用方案是 PyTorch 推理。
- 当前提供同步单图上传接口；任务状态、持久化和并发仍需在后续后端联调中确定。

## 11. 交给后端的最小约定

后端首次接入真实模型时，至少应保留以下信息：

- 原始文件名或任务内文件标识。
- `score_generated`、`score_semantics` 和 `prediction`。
- 定位掩膜文件路径或可访问资源标识。
- `mask_shape` 和 `mask_mean`。
- 实际使用的模型版本或权重哈希。
- 推理设备、处理状态和错误信息。

模型应在实际需要时初始化，不应在模块导入阶段加载大型 checkpoint。Web 文件校验、任务管理、结果存储和报告生成由后端负责，不应写入模型适配器。

## 12. 后端可执行结论

```text
backend_model_ready = true
detector_enabled = true
localizer_enabled = false
preprocess_mode = longest_side
detector_default_weight = models/weights/detector/rank8-img_size512-vit_b-best_f1.pth
```

必需文件为 SAM ViT-B 基础权重、Detector LoRA 权重、`models/source/` 推理源码和 `configs/default.yaml`。运行 `python scripts/verify_model_assets.py`、`python scripts/smoke_detect.py --device cpu --image sample_data/western_blots_dataset/real/real_img_00000.png` 以及 `python scripts/generate_detector_regression.py --device cpu` 均应成功。Localizer 启用前继续返回空定位结果。
