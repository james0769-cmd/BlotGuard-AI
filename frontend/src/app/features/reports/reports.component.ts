import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs';
import { MockDataService, UploadedFile } from '../../core/services/mock-data.service';
import { ReportService } from '../../core/services/report.service';

/**
 * ReportsComponent — 报告中心
 *
 * 功能：
 * 1. 展示所有已完成检测任务的报告列表
 * 2. 支持 PDF 报告下载/预览
 * 3. 显示每份报告的概要信息（风险等级、置信度等）
 * 4. 提供 PDF 文件专用上传入口
 */
@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressBarModule,
    MatSnackBarModule,
    MatTooltipModule,
    MatTabsModule,
  ],
  template: `
    <div class="reports-page">
      <header class="page-header">
        <h1>报告中心</h1>
        <p class="subtitle">查看和下载所有检测报告，上传 PDF 论文进行批量检测</p>
      </header>

      <mat-tab-group animationDuration="200ms">
        <!-- Tab 1: PDF 上传入口 -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon class="tab-icon">upload_file</mat-icon>
            PDF 检测
          </ng-template>

          <div class="tab-content">
            <div class="pdf-upload-section">
              <div class="upload-card"
                   [class.drag-over]="isDragOver()"
                   (drop)="onDrop($event)"
                   (dragover)="onDragOver($event)"
                   (dragleave)="onDragLeave($event)">
                <mat-icon class="big-icon">picture_as_pdf</mat-icon>
                <h3>上传 PDF 论文</h3>
                <p class="upload-desc">
                  系统将自动提取论文中的 Western Blot 图像并进行鉴伪分析
                </p>

                @if (uploadStatus() === 'uploading') {
                  <mat-progress-bar mode="determinate" [value]="uploadProgress()"></mat-progress-bar>
                  <p class="progress-text">正在上传... {{ uploadProgress() }}%</p>
                } @else if (uploadStatus() === 'success') {
                  <mat-icon class="success-icon">check_circle</mat-icon>
                  <p class="success-text">上传成功！文件已进入分析队列</p>
                } @else {
                  <input type="file" #pdfInput hidden
                         accept=".pdf"
                         (change)="onPdfSelected($event)" />
                  <button mat-raised-button color="primary" (click)="pdfInput.click()">
                    <mat-icon>folder_open</mat-icon>
                    选择 PDF 文件
                  </button>
                  <p class="hint">支持 .pdf 格式，最大 50MB</p>
                }
              </div>

              <div class="pdf-features">
                <div class="feature-item">
                  <mat-icon>auto_stories</mat-icon>
                  <div>
                    <strong>自动图像提取</strong>
                    <p>从 PDF 论文中自动识别并提取所有 Western Blot 图像</p>
                  </div>
                </div>
                <div class="feature-item">
                  <mat-icon>batch_prediction</mat-icon>
                  <div>
                    <strong>批量分析</strong>
                    <p>对提取的所有图像进行 AI 生成伪造检测</p>
                  </div>
                </div>
                <div class="feature-item">
                  <mat-icon>summarize</mat-icon>
                  <div>
                    <strong>生成综合报告</strong>
                    <p>输出包含所有检测结果的 PDF 分析报告</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </mat-tab>

        <!-- Tab 2: 报告列表 -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon class="tab-icon">description</mat-icon>
            分析报告
          </ng-template>

          <div class="tab-content">
            @if (completedTasks().length === 0) {
              <div class="empty-state">
                <mat-icon>inbox</mat-icon>
                <p>暂无已完成的检测报告</p>
                <p class="empty-hint">上传文件完成检测后，报告将在此处显示</p>
              </div>
            } @else {
              <div class="report-grid">
                @for (task of completedTasks(); track task.id) {
                  <mat-card class="report-card">
                    <mat-card-header>
                      <mat-icon mat-card-avatar class="report-avatar">
                        {{ isPdf(task.fileName) ? 'picture_as_pdf' : 'image' }}
                      </mat-icon>
                      <mat-card-title class="report-title">{{ task.fileName }}</mat-card-title>
                      <mat-card-subtitle>{{ task.uploadTime }}</mat-card-subtitle>
                    </mat-card-header>

                    <mat-card-content>
                      <div class="report-meta">
                        <mat-chip [style.backgroundColor]="getRiskBgColor(task.scoreGenerated)">
                          {{ getRiskLabel(task.scoreGenerated) }}
                        </mat-chip>
                        <span class="score-display">
                          生成概率:
                          <strong [style.color]="getScoreColor(task.scoreGenerated)">
                            {{ task.scoreGenerated != null ? (task.scoreGenerated * 100).toFixed(1) + '%' : '--' }}
                          </strong>
                        </span>
                      </div>
                    </mat-card-content>

                    <mat-card-actions align="end">
                      <button mat-button (click)="viewDetail(task.id)" matTooltip="查看详情">
                        <mat-icon>visibility</mat-icon>
                        详情
                      </button>
                      <button mat-button color="primary" (click)="downloadTaskReport(task)"
                              [disabled]="downloadingId() === task.id" matTooltip="下载 PDF 报告">
                        <mat-icon>download</mat-icon>
                        {{ downloadingId() === task.id ? '下载中...' : '下载报告' }}
                      </button>
                    </mat-card-actions>
                  </mat-card>
                }
              </div>
            }
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .reports-page { padding: 24px; max-width: 1400px; margin: 0 auto; }
    .page-header { margin-bottom: 24px; }
    .page-header h1 { margin: 0 0 8px; font-size: 28px; }
    .subtitle { color: var(--mat-sys-on-surface-variant); margin: 0; }

    .tab-icon { margin-right: 8px; }
    .tab-content { padding: 24px 0; }

    /* PDF 上传区域 */
    .pdf-upload-section {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 32px;
      align-items: start;
    }
    @media (max-width: 768px) {
      .pdf-upload-section { grid-template-columns: 1fr; }
    }

    .upload-card {
      border: 2px dashed var(--mat-sys-outline-variant, #ccc);
      border-radius: 16px;
      padding: 48px 32px;
      text-align: center;
      transition: border-color 0.2s, background 0.2s;
      cursor: pointer;
    }
    .upload-card:hover,
    .upload-card.drag-over {
      border-color: var(--mat-sys-primary, #1976d2);
      background: rgba(25, 118, 210, 0.04);
    }
    .upload-card .big-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
      color: var(--mat-sys-primary, #1976d2);
      margin-bottom: 16px;
    }
    .upload-card h3 { margin: 0 0 8px; font-size: 20px; }
    .upload-desc {
      color: var(--mat-sys-on-surface-variant);
      margin-bottom: 24px;
      font-size: 14px;
    }
    .hint { font-size: 12px; color: var(--mat-sys-on-surface-variant); margin-top: 12px; }
    .progress-text { margin-top: 12px; font-size: 14px; }
    .success-icon { font-size: 48px; width: 48px; height: 48px; color: #4caf50; }
    .success-text { color: #4caf50; font-weight: 500; }

    .pdf-features {
      display: flex;
      flex-direction: column;
      gap: 24px;
      padding-top: 16px;
    }
    .feature-item {
      display: flex;
      gap: 16px;
      align-items: flex-start;
    }
    .feature-item mat-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
      color: var(--mat-sys-primary, #1976d2);
      flex-shrink: 0;
    }
    .feature-item strong { display: block; margin-bottom: 4px; }
    .feature-item p { margin: 0; font-size: 13px; color: var(--mat-sys-on-surface-variant); }

    /* 空状态 */
    .empty-state {
      text-align: center;
      padding: 64px 24px;
      color: var(--mat-sys-on-surface-variant);
    }
    .empty-state mat-icon { font-size: 48px; width: 48px; height: 48px; margin-bottom: 16px; }
    .empty-hint { font-size: 13px; }

    /* 报告卡片 */
    .report-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 16px;
    }
    .report-card { border-radius: 12px; }
    .report-avatar {
      background: var(--mat-sys-primary-container, #e3f2fd);
      color: var(--mat-sys-primary, #1976d2);
      border-radius: 50%;
      padding: 8px;
      font-size: 24px;
      width: 40px;
      height: 40px;
    }
    .report-title {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 240px;
    }
    .report-meta {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-top: 12px;
    }
    .score-display { font-size: 14px; }
  `],
})
export class ReportsComponent {
  isDragOver = signal(false);
  uploadStatus = signal<'idle' | 'uploading' | 'success'>('idle');
  uploadProgress = signal(0);
  downloadingId = signal<string | null>(null);

  completedTasks = signal<UploadedFile[]>([]);

  constructor(
    private mockData: MockDataService,
    private reportService: ReportService,
    private snackBar: MatSnackBar,
    private router: Router,
  ) {
    // 筛选出已完成的任务
    const all = this.mockData.getUploadedFiles();
    this.completedTasks.set(all.filter(t => t.status === 'completed'));
  }

  isPdf(fileName: string): boolean {
    return fileName.toLowerCase().endsWith('.pdf');
  }

  // === PDF 上传 ===

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(false);

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handlePdfFile(files[0]);
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver.set(false);
  }

  onPdfSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handlePdfFile(input.files[0]);
      input.value = '';
    }
  }

  private handlePdfFile(file: File): void {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      this.snackBar.open('请选择 PDF 文件', '关闭', { duration: 3000 });
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      this.snackBar.open('文件过大，最大允许 50MB', '关闭', { duration: 3000 });
      return;
    }

    // 模拟上传流程
    this.uploadStatus.set('uploading');
    this.uploadProgress.set(0);

    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 15 + 5;
      if (progress >= 100) {
        progress = 100;
        clearInterval(interval);
        this.uploadProgress.set(100);
        this.uploadStatus.set('success');

        // 添加到 mock 数据
        this.mockData.addUploadedFile(file.name, file.size);
        const all = this.mockData.getUploadedFiles();
        this.completedTasks.set(all.filter(t => t.status === 'completed'));

        this.snackBar.open('PDF 上传成功，系统正在提取图像并分析', '关闭', { duration: 4000 });

        // 延迟重置
        setTimeout(() => this.uploadStatus.set('idle'), 3000);
      } else {
        this.uploadProgress.set(Math.round(progress));
      }
    }, 200);
  }

  // === 报告操作 ===

  viewDetail(taskId: string): void {
    this.router.navigate(['/detection', taskId]);
  }

  downloadTaskReport(task: UploadedFile): void {
    this.downloadingId.set(task.id);

    this.reportService.downloadReport(task.id).subscribe({
      next: (blob) => {
        this.reportService.triggerDownload(blob, `检测报告_${task.fileName}.pdf`);
        this.downloadingId.set(null);
        this.snackBar.open('报告下载成功', '关闭', { duration: 3000 });
      },
      error: (err) => {
        this.downloadingId.set(null);
        const message = err?.error?.message || err?.message || '报告下载失败，请稍后重试';
        this.snackBar.open(message, '关闭', { duration: 5000 });
      },
    });
  }

  // === 工具方法 ===

  getRiskLabel(score?: number): string {
    if (score == null) return '未知';
    if (score >= 0.8) return '高置信生成';
    if (score >= 0.5) return '高疑似生成';
    if (score >= 0.3) return '不确定';
    if (score >= 0.1) return '高疑似真实';
    return '高置信真实';
  }

  getRiskBgColor(score?: number): string {
    if (score == null) return '#f5f5f5';
    if (score >= 0.8) return '#ffcdd2';
    if (score >= 0.5) return '#fff3e0';
    if (score >= 0.3) return '#fff9c4';
    if (score >= 0.1) return '#c8e6c9';
    return '#e8f5e9';
  }

  getScoreColor(score?: number): string {
    if (score == null) return '#9e9e9e';
    if (score >= 0.8) return '#d32f2f';
    if (score >= 0.5) return '#f57c00';
    if (score >= 0.3) return '#f9a825';
    if (score >= 0.1) return '#66bb6a';
    return '#388e3c';
  }
}
