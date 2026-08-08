# 模型资产

推理所需的最小模型源码已经跟踪在 `models/source/`。训练脚本、实验结果和历史工作区不属于系统运行依赖。

## 权重目录

将团队统一版本的三份权重放到以下位置：

```text
models/weights/
├── sam_vit_b_01ec64.pth
├── detector/
│   └── rank8-full12-img_size512-vit_b-blots20-best_f1.pth
└── localizer/
    └── rank8-img_size1024-vit_b-best_f1.pth
```

macOS/Linux 示例：

```bash
mkdir -p models/weights/detector models/weights/localizer
cp /path/to/sam_vit_b_01ec64.pth models/weights/
cp /path/to/detector-best-f1.pth \
  models/weights/detector/rank8-full12-img_size512-vit_b-blots20-best_f1.pth
cp /path/to/localizer-best-f1.pth \
  models/weights/localizer/rank8-img_size1024-vit_b-best_f1.pth
```

Windows PowerShell 示例：

```powershell
New-Item -ItemType Directory -Force models\weights\detector, models\weights\localizer
Copy-Item C:\path\sam_vit_b_01ec64.pth models\weights\
Copy-Item C:\path\detector-best-f1.pth models\weights\detector\rank8-full12-img_size512-vit_b-blots20-best_f1.pth
Copy-Item C:\path\localizer-best-f1.pth models\weights\localizer\rank8-img_size1024-vit_b-best_f1.pth
```

## 校验

权重版本、大小和 SHA-256 记录在 `models/manifest.yaml`。放置完成后运行：

```bash
python scripts/verify_model_assets.py
```

只有三项均显示 `OK` 时，才使用这些权重进行联调或模型回归。

## 源码说明

- `source/segment_anything/`：检测与定位共同使用的 SAM 推理源码。
- `source/classifier/`：整图检测使用的 FCN 分类器。
- `third_party/segment-anything-LICENSE.txt`：SAM 第三方许可。

历史目录 `sam_lora_aigc_detect/` 与 `segment-anything-main_lora/` 可继续用于训练和实验，但系统运行不再依赖它们。
