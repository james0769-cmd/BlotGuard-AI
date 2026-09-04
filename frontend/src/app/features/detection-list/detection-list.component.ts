import { Component, computed, signal, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FormsModule } from '@angular/forms';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Subject, takeUntil } from 'rxjs';
import { TaskService } from '../../core/services/task.service';
import { RiskLevel } from '../../core/services/task.service';
import {
  RiskFilter,
  riskBackground,
  riskForeground,
  riskLabel,
} from '../../core/risk-level';

interface TaskCard {
  id: string;
  fileName: string;
  fileSize: number;
  uploadTime: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  overallScore?: number | null;
  riskLevel?: RiskLevel;
  applicable?: boolean;
  domainMessage?: string;
  errorMessage?: string;
}

const HISTORY_KEY = 'blotguard_upload_history';

@Component({
  selector: 'app-detection-list',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatChipsModule,
    MatButtonModule,
    MatIconModule,
    MatButtonToggleModule,
    MatTooltipModule,
    FormsModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="detection-list-page">
      <header class="page-header">
        <h1>鉴伪分析</h1>
        <p class="subtitle">查看所有检测任务的分析结果和历史记录</p>
        <p class="experimental-note">五级风险为实验性结果；DDPM/Pix2Pix 区分能力仍待改进，请人工复核。</p>
      </header>

      <div class="filter-bar">
        <mat-button-toggle-group [ngModel]="riskFilter()" (ngModelChange)="riskFilter.set($event)"
                                 hideSingleSelectionIndicator>
          <mat-button-toggle value="all">全部 ({{ allTasks().length }})</mat-button-toggle>
          <mat-button-toggle value="very_high">高置信生成 ({{ veryHighCount() }})</mat-button-toggle>
          <mat-button-toggle value="high">高疑似生成 ({{ highCount() }})</mat-button-toggle>
          <mat-button-toggle value="medium">不确定 ({{ mediumCount() }})</mat-button-toggle>
          <mat-button-toggle value="low">高疑似真实 ({{ lowCount() }})</mat-button-toggle>
          <mat-button-toggle value="very_low">高置信真实 ({{ veryLowCount() }})</mat-button-toggle>
        </mat-button-toggle-group>
      </div>

      @if (filteredTasks().length === 0) {
        <div class="empty-state">
          <mat-icon>inbox</mat-icon>
          <p>暂无检测记录</p>
          <p class="empty-hint">在工作台上传文件完成检测后，结果将在此显示</p>
        </div>
      } @else {
        <div class="task-grid">
          @for (task of filteredTasks(); track task.id) {
            <div class="task-card" (click)="openDetail(task.id)">
              <div class="card-header">
                <mat-icon [style.color]="getStatusIconColor(task.status)">
                  {{ getStatusIcon(task.status) }}
                </mat-icon>
                <span class="file-name">{{ task.fileName }}</span>
                @if (task.status === 'processing') {
                  <span class="polling-dot"></span>
                }
                @if (task.status === 'completed' || task.status === 'failed') {
                  <button mat-icon-button class="delete-button"
                          (click)="deleteTask($event, task)"
                          matTooltip="永久删除任务、图片和报告">
                    <mat-icon>delete_outline</mat-icon>
                  </button>
                }
              </div>
              <div class="card-body">
                @if (task.status === 'completed' && task.applicable === false) {
                  <div class="domain-rejection" role="status">
                    <mat-icon>image_not_supported</mat-icon>
                    <div>
                      <strong>非 Western Blot，无法鉴伪</strong>
                      <span>{{ task.domainMessage }}</span>
                    </div>
                  </div>
                } @else if (task.status === 'completed' && task.overallScore != null) {
                  <div class="score-row">
                    <span class="score-label">生成概率</span>
                    <span class="score-value" [style.color]="getScoreColor(task.riskLevel)">
                      {{ (task.overallScore * 100).toFixed(1) }}%
                    </span>
                  </div>
                  <div class="meta-row">
                    <mat-chip [style.backgroundColor]="getRiskBgColor(task.riskLevel)">
                      {{ getRiskLabel(task.riskLevel) }}
                    </mat-chip>
                    <span class="status-text">{{ getStatusLabel(task.status) }}</span>
                  </div>
                } @else {
                  <div class="score-row">
                    <span class="score-label">状态</span>
                    <span class="status-big">{{ getStatusLabel(task.status) }}</span>
                  </div>
                }
                @if (task.errorMessage) {
                  <div class="task-error" role="alert">
                    <mat-icon>error_outline</mat-icon>
                    <span>{{ task.errorMessage }}</span>
                  </div>
                }
                <div class="time-row">
                  <mat-icon>schedule</mat-icon>
                  <span>{{ task.uploadTime }}</span>
                  <span class="file-size">{{ formatFileSize(task.fileSize) }}</span>
                </div>
              </div>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .detection-list-page { padding: 24px; max-width: 1400px; margin: 0 auto; }
    .page-header { margin-bottom: 24px; }
    .page-header h1 { margin: 0 0 8px; font-size: 28px; }
    .subtitle { color: var(--mat-sys-on-surface-variant); margin: 0; }
    .experimental-note { margin: 8px 0 0; color: #92400e; font-size: 13px; }
    .filter-bar { margin-bottom: 24px; }

    .empty-state {
      text-align: center; padding: 64px 24px; color: var(--mat-sys-on-surface-variant);
    }
    .empty-state mat-icon { font-size: 48px; width: 48px; height: 48px; margin-bottom: 16px; }
    .empty-hint { font-size: 13px; color: #bbb; }

    .task-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 16px;
    }

    .task-card {
      border: 1px solid var(--mat-sys-outline-variant, #e0e0e0);
      border-radius: 12px; padding: 16px; cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
      background: var(--mat-sys-surface, #fff);
    }
    .task-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.08); }

    .card-header {
      display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
    }
    .file-name {
      font-weight: 500; overflow: hidden; text-overflow: ellipsis;
      white-space: nowrap; flex: 1;
    }
    .polling-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: #ff9800; animation: pulse 1.5s infinite;
    }
    .delete-button { color: #b91c1c; flex: 0 0 auto; }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }

    .card-body { display: flex; flex-direction: column; gap: 8px; }

    .score-row {
      display: flex; justify-content: space-between; align-items: center;
    }
    .score-label { font-size: 13px; color: var(--mat-sys-on-surface-variant); }
    .score-value { font-size: 20px; font-weight: 600; }
    .status-big { font-size: 18px; font-weight: 500; color: #6b7280; }

    .task-error {
      display: flex; align-items: flex-start; gap: 6px;
      padding: 8px; border-radius: 6px;
      color: #b91c1c; background: #fef2f2; font-size: 12px;
      mat-icon { flex: 0 0 auto; font-size: 16px; width: 16px; height: 16px; }
    }
    .domain-rejection {
      display: flex; align-items: flex-start; gap: 8px; padding: 10px;
      border-radius: 7px; color: #854d0e; background: #fffbeb; font-size: 12px;
    }
    .domain-rejection mat-icon { color: #d97706; flex: 0 0 auto; }
    .domain-rejection strong, .domain-rejection span { display: block; }
    .domain-rejection span { margin-top: 3px; color: #78716c; line-height: 1.4; }

    .meta-row { display: flex; align-items: center; gap: 8px; }
    .status-text { font-size: 12px; color: var(--mat-sys-on-surface-variant); }

    .time-row {
      display: flex; align-items: center; gap: 4px;
      font-size: 12px; color: var(--mat-sys-on-surface-variant);
      mat-icon { font-size: 14px; width: 14px; height: 14px; }
    }
    .file-size { margin-left: auto; color: #9ca3af; }
  `],
})
export class DetectionListComponent implements OnInit, OnDestroy {
  riskFilter = signal<RiskFilter>('all');
  allTasks = signal<TaskCard[]>([]);
  private readonly destroy$ = new Subject<void>();

  constructor(
    private taskService: TaskService,
    private router: Router,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    // 服务器是上传历史的唯一来源，页面可跨浏览器和刷新主动查看。
    this.taskService.listTasks().pipe(takeUntil(this.destroy$)).subscribe({
      next: tasks => {
        const cards = tasks.map(task => ({
          id: task.task_id,
          fileName: task.file_name,
          fileSize: task.file_size || 0,
          uploadTime: new Date(task.created_at).toLocaleString('zh-CN'),
          status: task.status,
          errorMessage: task.error_message ?? undefined,
        } satisfies TaskCard));
        this.allTasks.set(cards);
        for (const card of cards) this.pollTask(card.id);
      },
      error: err => {
        const message = err?.error?.message || '上传历史读取失败，请检查后端服务';
        this.snackBar.open(message, '关闭', { duration: 6000 });
      },
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private pollTask(taskId: string): void {
    this.taskService.pollTaskStatus(taskId, this.destroy$).subscribe({
      next: (status) => {
        this.updateTask(taskId, {
          status: status.status,
          errorMessage: status.status === 'failed'
            ? status.error_message || '检测任务失败'
            : undefined,
        });

        if (status.status === 'failed') {
          this.snackBar.open(status.error_message || '检测任务失败', '关闭', {
            duration: 6000,
          });
          return;
        }

        if (status.status === 'completed') {
          this.loadTaskResult(taskId);
        }
      },
      error: (err) => {
        const message = err?.error?.message || err?.message || '任务状态查询失败，请检查后端服务';
        this.updateTask(taskId, { errorMessage: message });
        this.snackBar.open(message, '关闭', { duration: 6000 });
      },
    });
  }

  private loadTaskResult(taskId: string): void {
    this.taskService.getTaskResult(taskId).pipe(
      takeUntil(this.destroy$),
    ).subscribe({
      next: (result) => {
        this.updateTask(taskId, {
          status: 'completed',
          overallScore: result.score_generated,
          riskLevel: result.risk_level ?? undefined,
          applicable: result.applicable,
          domainMessage: result.domain_message ?? undefined,
          errorMessage: undefined,
        });
      },
      error: (err) => {
        const message = err?.error?.message || err?.message || '检测结果加载失败';
        this.updateTask(taskId, { errorMessage: message });
        this.snackBar.open(message, '关闭', { duration: 6000 });
      },
    });
  }

  private updateTask(taskId: string, changes: Partial<TaskCard>): void {
    this.allTasks.update(tasks => tasks.map(task => (
      task.id === taskId ? { ...task, ...changes } : task
    )));
  }

  deleteTask(event: MouseEvent, task: TaskCard): void {
    event.stopPropagation();
    if (!window.confirm(`确定永久删除“${task.fileName}”吗？相关图片和报告也会删除。`)) return;
    this.taskService.deleteTask(task.id).subscribe({
      next: () => {
        this.allTasks.update(tasks => tasks.filter(item => item.id !== task.id));
        try {
          const raw = localStorage.getItem(HISTORY_KEY);
          const history = raw ? JSON.parse(raw) : [];
          localStorage.setItem(HISTORY_KEY, JSON.stringify(
            history.filter((item: { taskId: string }) => item.taskId !== task.id),
          ));
        } catch { /* server remains the source of truth */ }
        this.snackBar.open('任务、图片和报告已删除', '关闭', { duration: 2500 });
      },
      error: err => this.snackBar.open(
        err?.error?.message || '删除失败，请稍后重试',
        '关闭',
        { duration: 5000 },
      ),
    });
  }

  veryHighCount = computed(() => this.allTasks().filter(t => t.riskLevel === 'very_high').length);
  highCount = computed(() => this.allTasks().filter(t => t.riskLevel === 'high').length);
  mediumCount = computed(() => this.allTasks().filter(t => t.riskLevel === 'medium').length);
  lowCount = computed(() => this.allTasks().filter(t => t.riskLevel === 'low').length);
  veryLowCount = computed(() => this.allTasks().filter(t => t.riskLevel === 'very_low').length);

  filteredTasks = computed(() => {
    const tasks = this.allTasks();
    const filter = this.riskFilter();
    if (filter === 'all') return tasks;
    return tasks.filter(t => t.riskLevel === filter);
  });

  getRiskLabel(level?: RiskLevel): string {
    return riskLabel(level);
  }

  getRiskBgColor(level?: RiskLevel): string {
    return riskBackground(level);
  }

  getScoreColor(level?: RiskLevel): string {
    return riskForeground(level);
  }

  getStatusIcon(status: string): string {
    switch (status) {
      case 'completed': return 'check_circle';
      case 'processing': return 'hourglass_top';
      case 'pending': return 'schedule';
      case 'failed': return 'error';
      default: return 'help';
    }
  }

  getStatusIconColor(status: string): string {
    switch (status) {
      case 'completed': return '#4caf50';
      case 'processing': return '#ff9800';
      case 'failed': return '#f44336';
      default: return '#9e9e9e';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'completed': return '已完成';
      case 'processing': return '分析中';
      case 'pending': return '待处理';
      case 'failed': return '失败';
      default: return '未知';
    }
  }

  formatFileSize(bytes: number): string {
    if (!bytes || bytes < 1024) return '';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  openDetail(id: string): void {
    this.router.navigate(['/detection', id]);
  }
}
