import { Component, OnInit, OnDestroy, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
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

/**
 * DetectionDetailComponent — 鉴伪详情页（核心页面）
 *
 * 布局：
 * ┌─────────────────────────────────────────┐
 * │ 顶部: 文件名 + 整体评分 + 操作按钮       │
 * ├────────────────────────┬────────────────┤
 * │ 左侧: 双图对比画布      │ 右侧: 侧边栏    │
 * │ (缩放/平移/掩码叠加)   │ - 工具箱         │
 * │                        │ - 可疑区域列表    │
 * │                        │ - AI 概率图表     │
 * └────────────────────────┴────────────────┘
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
        <!-- 顶部信息栏 -->
        <header class="detail-header">
          <div class="header-left">
            <h2>{{ result()!.fileName }}</h2>
            <mat-chip-set>
              <mat-chip [highlighted]="result()!.overallRisk === 'high'"
                        [style.backgroundColor]="getRiskColor(result()!.overallRisk)">
                {{ getRiskLabel(result()!.overallRisk) }}
              </mat-chip>
              <mat-chip>
                综合置信度: {{ (result()!.overallConfidence * 100).toFixed(0) }}%
              </mat-chip>
            </mat-chip-set>
          </div>
          <div class="header-meta">
            <span class="meta-item">
              <mat-icon>model_training</mat-icon>
              {{ result()!.modelVersion }}
            </span>
            <span class="meta-item">
              <mat-icon>timer</mat-icon>
              {{ result()!.processingTime }}s
            </span>
          </div>
          <div class="header-actions">
            <button mat-stroked-button (click)="downloadReport()" [disabled]="downloading()">
              <mat-icon>picture_as_pdf</mat-icon>
              {{ downloading() ? '生成中...' : '导出报告' }}
            </button>
          </div>
        </header>

        <!-- 主体内容区 -->
        <div class="detail-body">
          <!-- 左侧：画布 -->
          <div class="canvas-section">
            <app-canvas-viewer
              #canvasViewer
              [originalImageUrl]="result()!.originalImageUrl"
              [maskImageUrl]="result()!.maskImageUrl"
              [brightness]="brightness()"
              [contrast]="contrast()">
            </app-canvas-viewer>
          </div>

          <!-- 右侧：工具/分析侧边栏 -->
          <aside class="sidebar-section">
            <app-forensic-toolbar
              (brightnessChange)="brightness.set($event)"
              (contrastChange)="contrast.set($event)"
              (maskOpacityChange)="onMaskOpacityChange($event)">
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

    .detail-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 24px;
      border-bottom: 1px solid #e5e7eb;
      background: #fff;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);

      .header-left {
        display: flex;
        align-items: center;
        gap: 16px;

        h2 {
          margin: 0;
          font-size: 1.1rem;
          font-weight: 600;
          color: #1a1a2e;
          letter-spacing: -0.01em;
        }
      }

      .header-meta {
        display: flex;
        align-items: center;
        gap: 20px;

        .meta-item {
          display: flex;
          align-items: center;
          gap: 5px;
          font-size: 0.82rem;
          color: #6b7280;
          background: #f3f4f6;
          padding: 4px 10px;
          border-radius: 6px;

          mat-icon {
            font-size: 15px;
            width: 15px;
            height: 15px;
            color: #9ca3af;
          }
        }
      }

      .header-actions button {
        border-radius: 8px;
        font-weight: 500;
      }
    }

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
  brightness = signal(100);
  contrast = signal(100);
  selectedRegionId = signal<number | null>(null);

  downloading = signal(false);
  private destroy$ = new Subject<void>();

  constructor(
    private route: ActivatedRoute,
    private mockDataService: MockDataService,
    private taskService: TaskService,
    private reportService: ReportService,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    const taskId = this.route.snapshot.paramMap.get('taskId') || '';

    // Gallery 样本 ID 格式：'real-xxxxx' / 'cyclegan-xxxxx' 等
    const isSample = this.mockDataService.getSampleEntries?.()?.some((s: { id: string }) => s.id === taskId);
    if (isSample || !taskId) {
      setTimeout(() => {
        this.result.set(this.mockDataService.getDetectionResult(taskId));
        this.loading.set(false);
      }, 400);
      return;
    }

    // 真实后端任务：轮询状态直到完成
    this.taskService.pollTaskStatus(taskId, this.destroy$).subscribe({
      next: (status) => {
        if (status.status === 'completed') {
          this.taskService.getTaskResult(taskId).subscribe({
            next: (r) => {
              this.result.set(this.mapTaskResult(taskId, r));
              this.loading.set(false);
            },
            error: () => {
              this.result.set(this.mockDataService.getDetectionResult(taskId));
              this.loading.set(false);
            },
          });
        } else if (status.status === 'failed') {
          this.loading.set(false);
          this.snackBar.open(status.error_message || '检测任务失败', '关闭', { duration: 5000 });
        }
      },
      error: () => {
        // 后端不可达时回退 mock
        this.result.set(this.mockDataService.getDetectionResult(taskId));
        this.loading.set(false);
      },
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private mapTaskResult(taskId: string, r: TaskResult): DetectionResult {
    return {
      id: taskId,
      fileName: r.filename,
      uploadTime: '',
      status: 'completed',
      originalImageUrl: r.original_image_url,
      maskImageUrl: r.mask_image_url,
      overallScore: r.overall_score,
      overallRisk: r.risk_level,
      overallConfidence: r.overall_score,
      modelVersion: r.model_version,
      processingTime: r.processing_time,
      suspectRegions: r.suspect_regions,
      modelProbabilities: r.model_probabilities,
    };
  }

  onRegionSelected(region: SuspectRegion): void {
    this.selectedRegionId.set(region.id);
    // TODO: 后续可以让画布自动平移到该区域
  }

  onMaskOpacityChange(opacity: number): void {
    this.canvasViewer?.setMaskOpacity(opacity);
  }

  /** 下载 PDF 报告 */
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

  getRiskColor(risk: string): string {
    switch (risk) {
      case 'high': return '#ffcdd2';
      case 'medium': return '#fff3e0';
      case 'low': return '#e8f5e9';
      default: return '#f5f5f5';
    }
  }

  getRiskLabel(risk: string): string {
    switch (risk) {
      case 'high': return '高风险';
      case 'medium': return '中风险';
      case 'low': return '低风险';
      default: return '未知';
    }
  }
}
