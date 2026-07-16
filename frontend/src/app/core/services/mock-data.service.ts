import { Injectable } from '@angular/core';

/**
 * MockDataService — 模拟后端返回的数据
 * 在后端接口对接之前，用这个服务驱动前端开发
 * 后端就绪后，只需将调用切换到真实 API 即可
 */

/** 单个可疑区域 */
export interface SuspectRegion {
  id: number;
  label: string;
  confidence: number; // 0~1
  bbox: { x: number; y: number; width: number; height: number }; // 相对于原图的比例坐标
  description: string;
}

/** AI 模型概率分布 */
export interface ModelProbability {
  model: string; // 'CycleGAN' | 'DDPM' | 'Pix2Pix' | 'StyleGAN2-ADA'
  probability: number; // 0~1
}

/** 完整的检测结果 */
export interface DetectionResult {
  id: string;
  fileName: string;
  uploadTime: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  originalImageUrl: string;
  maskImageUrl: string; // SAM/LoRA 生成的掩码叠加图
  overallScore: number; // 综合伪造置信度 0~1
  overallRisk: 'high' | 'medium' | 'low';
  overallConfidence: number; // 0~1
  modelVersion: string; // 模型版本号
  processingTime: number; // 处理耗时（秒）
  suspectRegions: SuspectRegion[];
  modelProbabilities: ModelProbability[];
}

/** 已上传文件记录（工作台列表用） */
export interface UploadedFile {
  id: string;
  fileName: string;
  fileSize: number; // bytes
  uploadTime: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  overallScore?: number;
}

// 内联 SVG 占位图（不依赖外网）
const PLACEHOLDER_ORIGINAL = `data:image/svg+xml,${encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
  <rect fill="#f5f5f5" width="800" height="600"/>
  <rect fill="#e0e0e0" x="80" y="100" width="640" height="400" rx="8"/>
  <!-- 模拟 Western Blot 条带 -->
  <rect fill="#333" x="150" y="180" width="60" height="240" rx="4" opacity="0.8"/>
  <rect fill="#555" x="240" y="200" width="60" height="200" rx="4" opacity="0.7"/>
  <rect fill="#333" x="330" y="170" width="60" height="250" rx="4" opacity="0.9"/>
  <rect fill="#666" x="420" y="210" width="60" height="190" rx="4" opacity="0.6"/>
  <rect fill="#333" x="510" y="185" width="60" height="230" rx="4" opacity="0.85"/>
  <rect fill="#555" x="600" y="195" width="60" height="210" rx="4" opacity="0.75"/>
  <text x="400" y="560" text-anchor="middle" fill="#999" font-size="14" font-family="sans-serif">Western Blot — 原始图像</text>
</svg>`)}`;

const PLACEHOLDER_MASK = `data:image/svg+xml,${encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
  <rect fill="transparent" width="800" height="600"/>
  <!-- 高亮可疑区域 -->
  <rect fill="rgba(244,67,54,0.35)" x="130" y="160" width="100" height="280" rx="6"/>
  <rect fill="rgba(255,152,0,0.3)" x="390" y="60" width="160" height="180" rx="6"/>
  <rect fill="rgba(255,193,7,0.25)" x="540" y="360" width="80" height="90" rx="6"/>
  <!-- 标注框 -->
  <rect fill="none" stroke="#f44336" stroke-width="2" x="130" y="160" width="100" height="280" rx="6" stroke-dasharray="6 3"/>
  <rect fill="none" stroke="#ff9800" stroke-width="2" x="390" y="60" width="160" height="180" rx="6" stroke-dasharray="6 3"/>
  <rect fill="none" stroke="#ffc107" stroke-width="2" x="540" y="360" width="80" height="90" rx="6" stroke-dasharray="6 3"/>
  <text x="400" y="560" text-anchor="middle" fill="#f44336" font-size="14" font-family="sans-serif">SAM/LoRA 检测掩码叠加</text>
</svg>`)}`;

@Injectable({ providedIn: 'root' })
export class MockDataService {
  private uploadedFiles: UploadedFile[] = [
    {
      id: 'det-001',
      fileName: 'western_blot_sample_01.png',
      fileSize: 2_450_000,
      uploadTime: '2026-06-26 10:32:15',
      status: 'completed',
      overallScore: 0.87,
    },
    {
      id: 'det-002',
      fileName: '论文图3_实验结果.pdf',
      fileSize: 5_120_000,
      uploadTime: '2026-06-26 09:15:03',
      status: 'completed',
      overallScore: 0.23,
    },
    {
      id: 'det-003',
      fileName: 'gel_image_fig2b.jpg',
      fileSize: 1_800_000,
      uploadTime: '2026-06-26 08:45:22',
      status: 'processing',
    },
    {
      id: 'det-004',
      fileName: 'supplementary_figure_S1.docx',
      fileSize: 8_900_000,
      uploadTime: '2026-06-25 16:20:11',
      status: 'pending',
    },
  ];

  /** 获取上传文件列表 */
  getUploadedFiles(): UploadedFile[] {
    return [...this.uploadedFiles];
  }

  /** 模拟新增上传文件 */
  addUploadedFile(fileName: string, fileSize: number): void {
    const newFile: UploadedFile = {
      id: `det-${String(this.uploadedFiles.length + 1).padStart(3, '0')}`,
      fileName,
      fileSize,
      uploadTime: new Date().toLocaleString('zh-CN', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      }).replace(/\//g, '-'),
      status: 'processing',
    };
    this.uploadedFiles.unshift(newFile);
  }

  /** 模拟检测结果 */
  getDetectionResult(id: string): DetectionResult {
    return {
      id,
      fileName: 'western_blot_sample_01.png',
      uploadTime: '2026-06-26 10:32:15',
      status: 'completed',
      originalImageUrl: PLACEHOLDER_ORIGINAL,
      maskImageUrl: PLACEHOLDER_MASK,
      overallScore: 0.87,
      overallRisk: 'high',
      overallConfidence: 0.87,
      modelVersion: 'SAM-LoRA v1.2.0',
      processingTime: 12.4,
      suspectRegions: [
        {
          id: 1,
          label: '条带复制区域',
          confidence: 0.92,
          bbox: { x: 0.2, y: 0.3, width: 0.15, height: 0.25 },
          description: '检测到该区域存在明显的条带重复模式，疑似通过复制粘贴生成',
        },
        {
          id: 2,
          label: '背景不一致区域',
          confidence: 0.78,
          bbox: { x: 0.5, y: 0.1, width: 0.2, height: 0.3 },
          description: '该区域背景噪声分布与周围区域显著不同，可能经过后处理',
        },
        {
          id: 3,
          label: '边缘伪影',
          confidence: 0.65,
          bbox: { x: 0.7, y: 0.6, width: 0.1, height: 0.15 },
          description: '检测到边缘存在 GAN 生成特有的棋盘格伪影',
        },
      ],
      modelProbabilities: [
        { model: 'CycleGAN', probability: 0.12 },
        { model: 'DDPM', probability: 0.05 },
        { model: 'Pix2Pix', probability: 0.71 },
        { model: 'StyleGAN2-ADA', probability: 0.12 },
      ],
    };
  }
}
