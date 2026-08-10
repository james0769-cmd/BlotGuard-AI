import { Injectable } from '@angular/core';
import { RiskLevel } from './task.service';

export interface SuspectRegion {
  id: number;
  label: string;
  confidence: number;
  bbox: { x: number; y: number; width: number; height: number };
  description: string;
}

export interface ModelProbability {
  model: string;
  probability: number;
}

export interface DetectionResult {
  id: string;
  fileName: string;
  uploadTime: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  originalImageUrl: string;
  maskAvailable: boolean;
  maskImageUrl: string | null;
  localizationMessage: string;
  scoreGenerated: number;
  riskLevel: RiskLevel;
  riskLevelIsExperimental: true;
  modelVersion: string;
  processingTime: number;
  suspectRegions: SuspectRegion[];
  modelProbabilities: ModelProbability[];
}

export interface UploadedFile {
  id: string;
  fileName: string;
  fileSize: number;
  uploadTime: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  scoreGenerated?: number;
}

export interface SampleEntry {
  id: string;
  fileName: string;
  assetPath: string;
  generator: string;
  expectedClass: 'original' | 'generated';
  scoreGenerated: number;
  prediction: 'original' | 'generated';
  modelVersion: string;
}

const MODEL_VERSION = 'detector-sam-vit-b-lora-r8-all-img512-51265aec';
const RISK_BOUNDARIES = [0.1186554090, 0.2370573707, 0.4702857587, 0.6720226015];

function riskLevelForScore(score: number): RiskLevel {
  if (score < RISK_BOUNDARIES[0]) return 'very_low';
  if (score < RISK_BOUNDARIES[1]) return 'low';
  if (score < RISK_BOUNDARIES[2]) return 'medium';
  if (score < RISK_BOUNDARIES[3]) return 'high';
  return 'very_high';
}

// 25 张样本数据，来自 sample_data/western_blots_dataset/detector_golden.json
export const SAMPLE_ENTRIES: SampleEntry[] = [
  { id: 'real-00000', fileName: 'real_img_00000.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_00000.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.0930, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-01183', fileName: 'real_img_01183.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_01183.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.3452, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-02366', fileName: 'real_img_02366.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_02366.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.0002, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-03549', fileName: 'real_img_03549.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_03549.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.1407, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-04732', fileName: 'real_img_04732.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_04732.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.1193, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-05916', fileName: 'real_img_05916.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_05916.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.0820, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-07099', fileName: 'real_img_07099.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_07099.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.0025, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-08282', fileName: 'real_img_08282.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_08282.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.2629, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-09465', fileName: 'real_img_09465.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_09465.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.0711, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-10649', fileName: 'real_img_10649.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_10649.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.1665, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-11832', fileName: 'real_img_11832.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_11832.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.0740, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-13015', fileName: 'real_img_13015.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_13015.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.0951, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-14199', fileName: 'real_img_14199.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_14199.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.2701, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'stylegan2ada-00000', fileName: 'stylegan2ada_img_00000.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/stylegan2ada/stylegan2ada_img_00000.png', generator: 'stylegan2ada', expectedClass: 'generated', scoreGenerated: 1.0000, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'stylegan2ada-02999', fileName: 'stylegan2ada_img_02999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/stylegan2ada/stylegan2ada_img_02999.png', generator: 'stylegan2ada', expectedClass: 'generated', scoreGenerated: 0.9999, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'stylegan2ada-05999', fileName: 'stylegan2ada_img_05999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/stylegan2ada/stylegan2ada_img_05999.png', generator: 'stylegan2ada', expectedClass: 'generated', scoreGenerated: 0.9459, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'cyclegan-00000', fileName: 'cyclegan_img_00000.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/cyclegan/cyclegan_img_00000.png', generator: 'cyclegan', expectedClass: 'generated', scoreGenerated: 0.8384, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'cyclegan-02999', fileName: 'cyclegan_img_02999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/cyclegan/cyclegan_img_02999.png', generator: 'cyclegan', expectedClass: 'generated', scoreGenerated: 0.6313, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'cyclegan-05999', fileName: 'cyclegan_img_05999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/cyclegan/cyclegan_img_05999.png', generator: 'cyclegan', expectedClass: 'generated', scoreGenerated: 1.0000, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'pix2pix-00000', fileName: 'pix2pix_img_00000.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/pix2pix/pix2pix_img_00000.png', generator: 'pix2pix', expectedClass: 'generated', scoreGenerated: 1.0000, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'pix2pix-02999', fileName: 'pix2pix_img_02999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/pix2pix/pix2pix_img_02999.png', generator: 'pix2pix', expectedClass: 'generated', scoreGenerated: 1.0000, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'pix2pix-05999', fileName: 'pix2pix_img_05999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/pix2pix/pix2pix_img_05999.png', generator: 'pix2pix', expectedClass: 'generated', scoreGenerated: 0.9204, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'ddpm-00000', fileName: 'ddpm_img_00000.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/ddpm/ddpm_img_00000.png', generator: 'ddpm', expectedClass: 'generated', scoreGenerated: 0.1886, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'ddpm-02999', fileName: 'ddpm_img_02999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/ddpm/ddpm_img_02999.png', generator: 'ddpm', expectedClass: 'generated', scoreGenerated: 0.8075, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'ddpm-05999', fileName: 'ddpm_img_05999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/ddpm/ddpm_img_05999.png', generator: 'ddpm', expectedClass: 'generated', scoreGenerated: 0.2516, prediction: 'original', modelVersion: MODEL_VERSION },
];

@Injectable({ providedIn: 'root' })
export class MockDataService {
  private uploadedFiles: UploadedFile[] = SAMPLE_ENTRIES.slice(0, 6).map((e, i) => ({
    id: e.id,
    fileName: e.fileName,
    fileSize: 1_500_000 + i * 300_000,
    uploadTime: '2026-07-23 10:00:00',
    status: 'completed' as const,
    scoreGenerated: e.scoreGenerated,
  }));

  getSampleEntries(): SampleEntry[] {
    return SAMPLE_ENTRIES;
  }

  getUploadedFiles(): UploadedFile[] {
    return [...this.uploadedFiles];
  }

  addUploadedFile(fileName: string, fileSize: number): void {
    const newFile: UploadedFile = {
      id: `upload-${Date.now()}`,
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

  getDetectionResult(id: string): DetectionResult {
    const entry = SAMPLE_ENTRIES.find((e) => e.id === id) ?? SAMPLE_ENTRIES[0];
    return {
      id: entry.id,
      fileName: entry.fileName,
      uploadTime: '2026-07-23 10:00:00',
      status: 'completed',
      originalImageUrl: entry.assetPath,
      maskAvailable: false,
      maskImageUrl: null,
      localizationMessage: '当前版本不提供区域定位',
      scoreGenerated: entry.scoreGenerated,
      riskLevel: riskLevelForScore(entry.scoreGenerated),
      riskLevelIsExperimental: true,
      modelVersion: entry.modelVersion,
      processingTime: 8.3,
      suspectRegions: [],
      modelProbabilities: [],
    };
  }
}
