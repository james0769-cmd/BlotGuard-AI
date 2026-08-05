import { Injectable } from '@angular/core';

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
  overallScore: number;
  overallRisk: 'unavailable';
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
  overallScore?: number;
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

const MODEL_VERSION = 'detector-sam-vit-b-lora-r8-l0-5-img512-4939e568';

// 25 张样本数据，来自 sample_data/western_blots_dataset/detector_golden.json
export const SAMPLE_ENTRIES: SampleEntry[] = [
  { id: 'real-00000', fileName: 'real_img_00000.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_00000.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.0759, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-01183', fileName: 'real_img_01183.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_01183.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.8236, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'real-02366', fileName: 'real_img_02366.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_02366.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.0183, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-03549', fileName: 'real_img_03549.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_03549.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.1660, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-04732', fileName: 'real_img_04732.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_04732.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.4413, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-05916', fileName: 'real_img_05916.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_05916.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.1294, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-07099', fileName: 'real_img_07099.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_07099.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.2623, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-08282', fileName: 'real_img_08282.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_08282.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.0663, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-09465', fileName: 'real_img_09465.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_09465.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.0122, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-10649', fileName: 'real_img_10649.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_10649.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.3519, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-11832', fileName: 'real_img_11832.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_11832.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.1020, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-13015', fileName: 'real_img_13015.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_13015.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.0972, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'real-14199', fileName: 'real_img_14199.png', assetPath: 'assets/sample_data/western_blots_dataset/real/real_img_14199.png', generator: 'real', expectedClass: 'original', scoreGenerated: 0.6710, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'stylegan2ada-00000', fileName: 'stylegan2ada_img_00000.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/stylegan2ada/stylegan2ada_img_00000.png', generator: 'stylegan2ada', expectedClass: 'generated', scoreGenerated: 0.9844, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'stylegan2ada-02999', fileName: 'stylegan2ada_img_02999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/stylegan2ada/stylegan2ada_img_02999.png', generator: 'stylegan2ada', expectedClass: 'generated', scoreGenerated: 0.9783, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'stylegan2ada-05999', fileName: 'stylegan2ada_img_05999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/stylegan2ada/stylegan2ada_img_05999.png', generator: 'stylegan2ada', expectedClass: 'generated', scoreGenerated: 0.1728, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'cyclegan-00000', fileName: 'cyclegan_img_00000.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/cyclegan/cyclegan_img_00000.png', generator: 'cyclegan', expectedClass: 'generated', scoreGenerated: 0.4409, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'cyclegan-02999', fileName: 'cyclegan_img_02999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/cyclegan/cyclegan_img_02999.png', generator: 'cyclegan', expectedClass: 'generated', scoreGenerated: 0.8722, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'cyclegan-05999', fileName: 'cyclegan_img_05999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/cyclegan/cyclegan_img_05999.png', generator: 'cyclegan', expectedClass: 'generated', scoreGenerated: 0.9233, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'pix2pix-00000', fileName: 'pix2pix_img_00000.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/pix2pix/pix2pix_img_00000.png', generator: 'pix2pix', expectedClass: 'generated', scoreGenerated: 0.8662, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'pix2pix-02999', fileName: 'pix2pix_img_02999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/pix2pix/pix2pix_img_02999.png', generator: 'pix2pix', expectedClass: 'generated', scoreGenerated: 0.6790, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'pix2pix-05999', fileName: 'pix2pix_img_05999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/pix2pix/pix2pix_img_05999.png', generator: 'pix2pix', expectedClass: 'generated', scoreGenerated: 0.5705, prediction: 'generated', modelVersion: MODEL_VERSION },
  { id: 'ddpm-00000', fileName: 'ddpm_img_00000.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/ddpm/ddpm_img_00000.png', generator: 'ddpm', expectedClass: 'generated', scoreGenerated: 0.0255, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'ddpm-02999', fileName: 'ddpm_img_02999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/ddpm/ddpm_img_02999.png', generator: 'ddpm', expectedClass: 'generated', scoreGenerated: 0.1447, prediction: 'original', modelVersion: MODEL_VERSION },
  { id: 'ddpm-05999', fileName: 'ddpm_img_05999.png', assetPath: 'assets/sample_data/western_blots_dataset/synth/ddpm/ddpm_img_05999.png', generator: 'ddpm', expectedClass: 'generated', scoreGenerated: 0.0541, prediction: 'original', modelVersion: MODEL_VERSION },
];

@Injectable({ providedIn: 'root' })
export class MockDataService {
  private uploadedFiles: UploadedFile[] = SAMPLE_ENTRIES.slice(0, 6).map((e, i) => ({
    id: e.id,
    fileName: e.fileName,
    fileSize: 1_500_000 + i * 300_000,
    uploadTime: '2026-07-23 10:00:00',
    status: 'completed' as const,
    overallScore: e.scoreGenerated,
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
      overallScore: entry.scoreGenerated,
      overallRisk: 'unavailable',
      modelVersion: entry.modelVersion,
      processingTime: 8.3,
      suspectRegions: [],
      modelProbabilities: [],
    };
  }
}
