import { Component, OnDestroy, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, catchError, forkJoin, map, of, switchMap, takeUntil } from 'rxjs';
import { ReportService } from '../../core/services/report.service';
import { RiskLevel, TaskService } from '../../core/services/task.service';
import { riskBackground, riskForeground, riskLabel } from '../../core/risk-level';

interface ReportTask {
  id: string;
  fileName: string;
  fileSize: number;
  uploadTime: string;
  scoreGenerated: number | null;
  riskLevel: RiskLevel | null;
  applicable: boolean;
}

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
  ],
  template: `
    <div class="reports-page">
      <header class="page-header">
        <h1>报告中心</h1>
        <p class="subtitle">集中查看和下载已完成任务的检测报告</p>
        <p class="experimental-note">五级风险为实验性结果；DDPM/Pix2Pix 区分能力仍待改进。</p>
      </header>

      <section class="entry-note">
        <div class="entry-copy">
          <mat-icon>info</mat-icon>
          <div>
            <strong>图片、PDF 和 Word 文件统一从工作台上传</strong>
            <p>报告中心只保留已完成报告，避免同一文件出现两套上传状态和任务编号。</p>
          </div>
        </div>
        <button mat-raised-button color="primary" (click)="goToWorkspace()">
          <mat-icon>cloud_upload</mat-icon>
          前往工作台上传
        </button>
      </section>

      @if (loading()) {
        <div class="loading-state">
          <mat-spinner diameter="40"></mat-spinner>
          <p>正在同步真实任务状态...</p>
        </div>
      } @else if (completedTasks().length === 0) {
        <div class="empty-state">
          <mat-icon>inbox</mat-icon>
          <p>暂无已完成的检测报告</p>
          <p class="empty-hint">在工作台完成一次检测后，报告会显示在这里。</p>
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
                  @if (task.applicable) {
                    <mat-chip [style.backgroundColor]="getRiskBgColor(task.riskLevel)">
                      {{ getRiskLabel(task.riskLevel) }}
                    </mat-chip>
                    <span class="score-display">
                      生成风险分数：
                      <strong [style.color]="getScoreColor(task.riskLevel)">
                        {{ (task.scoreGenerated! * 100).toFixed(1) }}%
                      </strong>
                    </span>
                  } @else {
                    <mat-chip class="not-applicable-chip">非 Western Blot · 不适用</mat-chip>
                  }
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
  `,
  styles: [`
    .reports-page { padding: 24px; max-width: 1400px; margin: 0 auto; }
    .page-header { margin-bottom: 20px; }
    .page-header h1 { margin: 0 0 8px; font-size: 28px; }
    .subtitle { color: var(--mat-sys-on-surface-variant); margin: 0; }
    .experimental-note { margin: 8px 0 0; color: #92400e; font-size: 13px; }
    .entry-note {
      display: flex; align-items: center; justify-content: space-between; gap: 20px;
      padding: 18px 20px; margin-bottom: 24px; border-radius: 12px;
      background: #eef6ff; border: 1px solid #bfdbfe;
    }
    .entry-copy { display: flex; align-items: flex-start; gap: 12px; }
    .entry-copy > mat-icon { color: #1976d2; margin-top: 2px; }
    .entry-copy strong { display: block; margin-bottom: 4px; }
    .entry-copy p { margin: 0; color: #526274; font-size: 13px; }
    .loading-state, .empty-state {
      display: flex; flex-direction: column; align-items: center;
      text-align: center; padding: 64px 24px; color: var(--mat-sys-on-surface-variant);
    }
    .loading-state { gap: 12px; }
    .empty-state > mat-icon { font-size: 48px; width: 48px; height: 48px; margin-bottom: 16px; }
    .empty-hint { font-size: 13px; }
    .report-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px;
    }
    .report-card { border-radius: 12px; }
    .report-avatar {
      background: var(--mat-sys-primary-container, #e3f2fd); color: var(--mat-sys-primary, #1976d2);
      border-radius: 50%; padding: 8px; font-size: 24px; width: 40px; height: 40px;
    }
    .report-title {
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 240px;
    }
    .report-meta { display: flex; align-items: center; gap: 12px; margin-top: 12px; }
    .score-display { font-size: 14px; }
    .not-applicable-chip { background: #fef3c7; color: #92400e; }
    @media (max-width: 720px) {
      .entry-note { align-items: stretch; flex-direction: column; }
      .report-grid { grid-template-columns: 1fr; }
    }
  `],
})
export class ReportsComponent implements OnInit, OnDestroy {
  loading = signal(true);
  completedTasks = signal<ReportTask[]>([]);
  downloadingId = signal<string | null>(null);
  private readonly destroy$ = new Subject<void>();

  constructor(
    private taskService: TaskService,
    private reportService: ReportService,
    private snackBar: MatSnackBar,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.taskService.listTasks().pipe(
      switchMap(tasks => {
        const completed = tasks.filter(task => task.status === 'completed');
        if (!completed.length) return of([] as ReportTask[]);
        return forkJoin(completed.map(status =>
          this.taskService.getTaskResult(status.task_id).pipe(map(result => ({
            id: status.task_id,
            fileName: status.file_name,
            fileSize: status.file_size || 0,
            uploadTime: new Date(status.created_at).toLocaleString('zh-CN'),
            scoreGenerated: result.score_generated,
            riskLevel: result.risk_level,
            applicable: result.applicable,
          } satisfies ReportTask)), catchError(() => of(null))))
        ).pipe(map(results => results.filter((task): task is ReportTask => task !== null)));
      }),
      catchError(() => of([] as ReportTask[])),
      takeUntil(this.destroy$),
    ).subscribe(tasks => {
        this.completedTasks.set(tasks);
        this.loading.set(false);
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  goToWorkspace(): void {
    this.router.navigate(['/workspace']);
  }

  isPdf(fileName: string): boolean {
    return fileName.toLowerCase().endsWith('.pdf');
  }

  viewDetail(taskId: string): void {
    this.router.navigate(['/detection', taskId]);
  }

  downloadTaskReport(task: ReportTask): void {
    this.downloadingId.set(task.id);
    this.reportService.downloadReport(task.id).subscribe({
      next: blob => {
        this.reportService.triggerDownload(blob, `检测报告_${task.fileName}.pdf`);
        this.downloadingId.set(null);
        this.snackBar.open('报告下载成功', '关闭', { duration: 3000 });
      },
      error: err => {
        this.downloadingId.set(null);
        const message = err?.error?.message || err?.message || '报告下载失败，请稍后重试';
        this.snackBar.open(message, '关闭', { duration: 5000 });
      },
    });
  }

  getRiskLabel(level: RiskLevel | null): string {
    return riskLabel(level ?? undefined);
  }

  getRiskBgColor(level: RiskLevel | null): string {
    return riskBackground(level ?? undefined);
  }

  getScoreColor(level: RiskLevel | null): string {
    return riskForeground(level ?? undefined);
  }
}
