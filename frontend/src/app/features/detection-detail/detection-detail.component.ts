import { Component, OnInit, OnDestroy, ViewChild, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject } from 'rxjs';
import { CanvasViewerComponent } from './canvas-viewer/canvas-viewer.component';
import { SuspectListComponent } from './suspect-list/suspect-list.component';
import { ProbabilityChartComponent } from './probability-chart/probability-chart.component';
import { ForensicToolbarComponent } from './forensic-toolbar/forensic-toolbar.component';
import {
  MockDataService,
  DetectionResult,
  SuspectRegion,
} from '../../core/services/mock-data.service';
import { ReportService } from '../../core/services/report.service';
import { TaskService, TaskResult } from '../../core/services/task.service';

/** 多图任务中每张图片的展示数据 */
interface ImageItem {
  index: number;
  label: string;
  originalImageUrl: string;
  maskImageUrl: string;
  score?: number;
}

/**
 * DetectionDetailComponent — 鉴伪详情页
 *
 * 布局：
 * ┌──────────────────────────────────────────────────┐
 * │ 顶部: 文件类型标签 + 文件名 + 风险 + 报告按钮     │
 * │      图片切换器（多图时显示）                      │
 * ├─────────────────────────┬────────────────────────┤
 * │ 左侧: 双图对比画布       │ 右侧: 工具箱/区域/图表  │
 * └─────────────────────────┴────────────────────────┘
 */
@Component({
  selector: 'app-detection-detail',
  standalone: true,
  imports: [
    CommonModule,
    MatProgressSpinnerModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatSnackBarModule,
    MatTooltipModule,
    CanvasViewerComponent,
    SuspectListComponent,
    ProbabilityChartComponent,
    ForensicToolbarComponent,
  ],
  template: `
    @if (loading()) {
      <div class="loading-state">
        <mat-spinner diameter="48"></mat-spinner>
        <p>正在加载检测结果...</p>
      </div>
    } @else if (result()) {
      <div class="detail-page">
        <!-- === 顶部信息栏 === -->
        <header class="detail-header">
          <div class="header-top-row">
            <div class="header-left">
              <!-- 文件类型标签 -->
              <span class="file-type-badge" [class]="'type-' + fileType()">
                <mat-icon>{{ fileTypeIcon() }}</mat-icon>
                {{ fileTypeLabel() }}
              </span>
              <h2>{{ result()!.fileName }}</h2>
              <!-- 风险等级 -->
              <mat-chip [highlighted]="result()!.scoreGenerated >= 0.8"
                        [style.backgroundColor]="getRiskColor(result()!.scoreGenerated)">
                {{ getRiskLabel(result()!.scoreGenerated) }}
              </mat-chip>
              <mat-chip>
                置信度: {{ (result()!.scoreGenerated * 100).toFixed(0) }}%
              </mat-chip>
            </div>
            <div class="header-actions">
              @if (imageItems().length > 1) {
                <span class="page-indicator">
                  {{ selectedImageIndex() + 1 }} / {{ imageItems().length }}
                </span>
              }
              <!-- 报告下载 -->
              @if (isSample()) {
                <button mat-stroked-button disabled matTooltip="样本数据不支持报告下载">
                  <mat-icon>picture_as_pdf</mat-icon>
                  不可下载
                </button>
              } @else {
                <button mat-stroked-button color="accent"
                        (click)="downloadReport()" [disabled]="downloading()"
                        matTooltip="下载 PDF 检测报告">
                  <mat-icon>picture_as_pdf</mat-icon>
                  {{ downloading() ? '生成中...' : '下载报告' }}
                </button>
              }
            </div>
          </div>
          <!-- 元数据行 -->
          <div class="header-meta-row">
            <span class="meta-item">
              <mat-icon>description</mat-icon>
              {{ fileTypeLabel() }}
              @if (imageItems().length > 1) {
                · {{ imageItems().length }} 张图片
              }
            </span>
            <span class="meta-item">
              <mat-icon>timer</mat-icon>
              {{ result()!.processingTime }}s
            </span>
            <span class="meta-item" [matTooltip]="result()!.modelVersion">
              <mat-icon>model_training</mat-icon>
              {{ shortModelVersion() }}
            </span>
          </div>
          <!-- 图片切换器（多图时显示） -->
          @if (imageItems().length > 1) {
            <div class="image-switcher">
              <button mat-icon-button matTooltip="上一张"
                      [disabled]="selectedImageIndex() === 0"
                      (click)="selectImage(selectedImageIndex() - 1)">
                <mat-icon>chevron_left</mat-icon>
              </button>
              <div class="thumbnail-strip">
                @for (item of imageItems(); track item.index) {
                  <div class="thumbnail-item"
                       [class.active]="selectedImageIndex() === item.index"
                       (click)="selectImage(item.index)">
                    <img [src]="item.originalImageUrl" [alt]="item.label" />
                    <span class="thumb-label">{{ item.label }}</span>
                    @if (item.score != null) {
                      <span class="thumb-score"
                            [style.color]="getScoreColor(item.score)">
                        {{ (item.score * 100).toFixed(0) }}%
                      </span>
                    }
                  </div>
                }
              </div>
              <button mat-icon-button matTooltip="下一张"
                      [disabled]="selectedImageIndex() >= imageItems().length - 1"
                      (click)="selectImage(selectedImageIndex() + 1)">
                <mat-icon>chevron_right</mat-icon>
              </button>
            </div>
          }
        </header>

        <!-- === 主体内容区 === -->
        <div class="detail-body">
          <div class="canvas-section">
            <app-canvas-viewer
              #canvasViewer
              [originalImageUrl]="currentImage().originalImageUrl"
              [maskImageUrl]="currentImage().maskImageUrl"
              [hasMask]="!!currentImage().maskImageUrl"
              [brightness]="brightness()"
              [contrast]="contrast()">
            </app-canvas-viewer>
          </div>

          <aside class="sidebar-section">
            <app-forensic-toolbar
              [hasMask]="!!currentImage().maskImageUrl"
              (brightnessChange)="brightness.set($event)"
              (contrastChange)="contrast.set($event)"
              (maskOpacityChange)="onMaskOpacityChange($event)"
              (reset)="canvasViewer.resetView()">
            </app-forensic-toolbar>

            <app-suspect-list
              [regions]="result()!.suspectRegions"
              [selectedId]="selectedRegionId()"
              (regionSelected)="onRegionSelected($event)">
            </app-suspect-list>

            <app-probability-chart
              [probabilities]="result()!.modelProbabilities">
            </app-probability-chart>
          </aside>
        </div>
      </div>
    }
  `,
  styles: [`
    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 60vh;
      gap: 16px;
      color: #6b7280;
      animation: fadeIn 0.4s ease-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .detail-page {
      height: calc(100vh - 64px);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      animation: fadeIn 0.3s ease-out;
    }

    /* ====== 顶部信息栏 ====== */
    .detail-header {
      background: #fff;
      border-bottom: 1px solid #e5e7eb;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }

    .header-top-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 24px 8px;
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .header-left h2 {
      margin: 0;
      font-size: 1.1rem;
      font-weight: 600;
      color: #1a1a2e;
      letter-spacing: -0.01em;
      max-width: 360px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    /* 文件类型标签 */
    .file-type-badge {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 3px 10px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 600;
      white-space: nowrap;
    }
    .file-type-badge mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }
    .file-type-badge.type-image {
      background: #e3f2fd;
      color: #1565c0;
    }
    .file-type-badge.type-pdf {
      background: #fce4ec;
      color: #c62828;
    }
    .file-type-badge.type-docx {
      background: #e8f5e9;
      color: #2e7d32;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .header-actions button {
      border-radius: 8px;
      font-weight: 500;
    }
    .page-indicator {
      font-size: 0.85rem;
      font-weight: 500;
      color: #6b7280;
      background: #f3f4f6;
      padding: 4px 10px;
      border-radius: 6px;
    }

    /* 元数据行 */
    .header-meta-row {
      display: flex;
      align-items: center;
      gap: 20px;
      padding: 0 24px 8px;
    }
    .meta-item {
      display: flex;
      align-items: center;
      gap: 5px;
      font-size: 0.78rem;
      color: #6b7280;
    }
    .meta-item mat-icon {
      font-size: 15px;
      width: 15px;
      height: 15px;
      color: #9ca3af;
    }

    /* ====== 图片切换器 ====== */
    .image-switcher {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 16px 10px;
      background: #fafafa;
      border-top: 1px solid #f0f0f0;
    }
    .thumbnail-strip {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      flex: 1;
      padding: 2px 0;
    }
    .thumbnail-item {
      flex-shrink: 0;
      width: 64px;
      height: 48px;
      position: relative;
      border: 2px solid #e0e0e0;
      border-radius: 4px;
      overflow: hidden;
      cursor: pointer;
      transition: border-color 0.15s;
    }
    .thumbnail-item:hover {
      border-color: #90caf9;
    }
    .thumbnail-item.active {
      border-color: #1976d2;
      box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.2);
    }
    .thumbnail-item img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .thumb-label {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      background: rgba(0, 0, 0, 0.55);
      color: #fff;
      font-size: 9px;
      padding: 1px 4px;
      text-align: center;
    }
    .thumb-score {
      position: absolute;
      top: 2px;
      right: 3px;
      font-size: 9px;
      font-weight: 600;
      background: rgba(255, 255, 255, 0.85);
      padding: 0 2px;
      border-radius: 2px;
    }

    /* ====== 主体区 ====== */
    .detail-body {
      flex: 1;
      display: flex;
      overflow: hidden;
    }
    .canvas-section {
      flex: 1;
      min-width: 0;
      padding: 16px;
      background: #f9fafb;
    }
    .sidebar-section {
      width: 330px;
      border-left: 1px solid #e5e7eb;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
      padding: 16px;
      background: #fff;
    }
  `],
})
export class DetectionDetailComponent implements OnInit, OnDestroy {
  @ViewChild('canvasViewer') canvasViewer!: CanvasViewerComponent;

  result = signal<DetectionResult | null>(null);
  loading = signal(true);
  isSample = signal(false);
  brightness = signal(100);
  contrast = signal(100);
  selectedRegionId = signal<number | null>(null);
  selectedImageIndex = signal(0);

  downloading = signal(false);
  private destroy$ = new Subject<void>();

  /** 模型版本缩写 */
  shortModelVersion = computed(() => {
    const v = this.result()?.modelVersion || '';
    // 提取关键部分，如 "detector-sam-vit-b-lora-r8-l0-5-img512-4939e568"
    // → "SAM ViT-B LoRA r8"
    const match = v.match(/sam-vit-(\w)/);
    const loraMatch = v.match(/lora-r(\d+)/);
    if (match && loraMatch) {
      return `SAM ViT-${match[1].toUpperCase()} LoRA r${loraMatch[1]}`;
    }
    // 兜底：截断显示
    return v.length > 30 ? v.slice(0, 28) + '…' : v;
  });

  /** 从 result 构建多图列表 */
  imageItems = computed<ImageItem[]>(() => {
    const r = this.result();
    if (!r) return [];
    // TODO: 后续从后端返回的 items 数组构建多图列表
    // 当前仅支持单图，多图字段为未来扩展
    return [{
      index: 0,
      label: '第 1 张',
      originalImageUrl: r.originalImageUrl,
      maskImageUrl: r.maskImageUrl ?? '',
      score: r.scoreGenerated,
    }];
  });

  /** 当前选中图片 */
  currentImage = computed<ImageItem>(() => {
    const items = this.imageItems();
    const idx = this.selectedImageIndex();
    return items[idx] || items[0];
  });

  /** 文件类型（从文件名推断） */
  fileType = computed<'image' | 'pdf' | 'docx'>(() => {
    const name = this.result()?.fileName?.toLowerCase() || '';
    if (name.endsWith('.pdf')) return 'pdf';
    if (name.endsWith('.docx')) return 'docx';
    return 'image';
  });

  fileTypeIcon = computed(() => {
    switch (this.fileType()) {
      case 'pdf': return 'picture_as_pdf';
      case 'docx': return 'description';
      default: return 'image';
    }
  });

  fileTypeLabel = computed(() => {
    switch (this.fileType()) {
      case 'pdf': return 'PDF 文档';
      case 'docx': return 'Word 文档';
      default: return '图片文件';
    }
  });

  constructor(
    private route: ActivatedRoute,
    private mockDataService: MockDataService,
    private taskService: TaskService,
    private reportService: ReportService,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    const taskId = this.route.snapshot.paramMap.get('taskId') || '';

    const isMockSample = this.mockDataService.getSampleEntries?.()?.some((s: { id: string }) => s.id === taskId);
    if (isMockSample || !taskId) {
      this.isSample.set(true);
      setTimeout(() => {
        this.result.set(this.mockDataService.getDetectionResult(taskId));
        this.loading.set(false);
      }, 400);
      return;
    }

    this.taskService.pollTaskStatus(taskId, this.destroy$).subscribe({
      next: (status) => {
        if (status.status === 'completed') {
          this.taskService.getTaskResult(taskId).subscribe({
            next: (r) => {
              this.result.set(this.mapTaskResult(taskId, r));
              this.loading.set(false);
            },
            error: (err) => {
              this.loading.set(false);
              const message = err?.error?.message || err?.message || '获取检测结果失败';
              this.snackBar.open(message, '关闭', { duration: 6000 });
            },
          });
        } else if (status.status === 'failed') {
          this.loading.set(false);
          this.snackBar.open(status.error_message || '检测任务失败', '关闭', { duration: 6000 });
        }
      },
      error: (err) => {
        this.loading.set(false);
        const message = err?.error?.message || err?.message || '轮询任务状态失败，请检查网络连接';
        this.snackBar.open(message, '关闭', { duration: 6000 });
      },
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /** 切换图片 */
  selectImage(index: number): void {
    this.selectedImageIndex.set(index);
    this.canvasViewer?.resetView();
  }

  private mapTaskResult(taskId: string, r: TaskResult): DetectionResult {
    return {
      id: taskId,
      fileName: r.filename,
      uploadTime: '',
      status: 'completed',
      originalImageUrl: r.original_image_url,
      maskAvailable: r.mask_available,
      maskImageUrl: r.mask_image_url,
      localizationMessage: r.localization_message ?? '',
      scoreGenerated: r.score_generated,
      riskLevel: r.risk_level,
      riskLevelIsExperimental: r.risk_level_is_experimental,
      modelVersion: r.model_version,
      processingTime: r.processing_time,
      suspectRegions: r.suspect_regions,
      modelProbabilities: r.model_probabilities,
    };
  }

  onRegionSelected(region: SuspectRegion): void {
    this.selectedRegionId.set(region.id);
  }

  onMaskOpacityChange(opacity: number): void {
    this.canvasViewer?.setMaskOpacity(opacity);
  }

  downloadReport(): void {
    const r = this.result();
    if (!r) return;

    this.downloading.set(true);
    this.reportService.downloadReport(r.id).subscribe({
      next: (blob) => {
        this.reportService.triggerDownload(blob, `检测报告_${r.fileName}.pdf`);
        this.downloading.set(false);
        this.snackBar.open('报告下载成功', '关闭', { duration: 3000 });
      },
      error: () => {
        this.downloading.set(false);
        this.snackBar.open('报告下载失败，请稍后重试', '关闭', { duration: 4000 });
      },
    });
  }

  getRiskColor(score?: number): string {
    if (score == null) return '#f5f5f5';
    if (score >= 0.8) return '#ffcdd2';
    if (score >= 0.5) return '#fff3e0';
    if (score >= 0.3) return '#fff9c4';
    if (score >= 0.1) return '#c8e6c9';
    return '#e8f5e9';
  }

  getRiskLabel(score?: number): string {
    if (score == null) return '未知';
    if (score >= 0.8) return '高置信生成';
    if (score >= 0.5) return '高疑似生成';
    if (score >= 0.3) return '不确定';
    if (score >= 0.1) return '高疑似真实';
    return '高置信真实';
  }

  getScoreColor(score?: number): string {
    if (score == null) return '#9e9e9e';
    if (score >= 0.8) return '#d32f2f';
    if (score >= 0.5) return '#f57c00';
    if (score >= 0.3) return '#fbc02d';
    if (score >= 0.1) return '#66bb6a';
    return '#388e3c';
  }
}
