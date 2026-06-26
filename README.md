# 蛋白印迹AI检测系统

## 快速开始

### 1. 准备
确保项目根目录下已有：
```text
sam_lora_aigc_detect/
segment-anything-main_lora/
data/
```
### 2. 环境(CPU)
```bash
docker build -t wb-ai:cpu .
```
macOS / Linux：

```bash
DATA_DIR=/path/to/data
docker run --rm -it \
  -v "$PWD":/workspace \
  -v "$DATA_DIR":/data:ro \
  wb-ai:cpu
```
Windows PowerShell：
```powershell
$env:DATA_DIR="D:\path\to\data"
docker run --rm -it `
  -v ${PWD}:/workspace `
  -v ${env:DATA_DIR}:/data:ro `
  wb-ai:cpu
```

### 3. 检查环境

进入容器后执行：

```bash
python -c "import torch, torchvision, cv2, sklearn, numpy; print(torch.__version__, torchvision.__version__, numpy.__version__, cv2.__version__, torch.cuda.is_available())"
```

### 4. 检查模型

分类检测：

```bash
python scripts/smoke_detect.py \
  --device cpu \
  --image /data/western_blots/western_blots_dataset/real/real_img_04818.png
```

篡改定位：

```bash
python scripts/smoke_segment.py \
  --device cpu \
  --image /data/western_blots/western_blots_dataset/synth/stylegan2ada/stylegan2ada_img_00001.png \
  --output outputs/smoke_segment_mask.png
```
