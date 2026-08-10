import { Component, computed, signal, OnInit } from '@angular/core';
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
import { MockDataService, UploadedFile } from '../../core/services/mock-data.service';
import { TaskService } from '../../core/services/task.service';

interface TaskCard {
  id: string;
  fileName: string;
  fileSize: number;
  uploadTime: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  overallScore?: number;
  isMock: boolean;
}

type RiskFilter = 'all' | 'high' | 'suspected' | 'uncertain' | 'likely_real' | 'high_real';

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
      </header>

      <div class="filter-bar">
        <mat-button-toggle-group [(ngModel)]="riskFilter" hideSingleSelectionIndicator>
          <mat-button-toggle value="all">全部 ({{ allTasks().length }})</mat-button-toggle>
          <mat-button-toggle value="high">高置信生成 ({{ highCount() }})</mat-button-toggle>
          <mat-button-toggle value="suspected">高疑似生成 ({{ suspectedCount() }})</mat-button-toggle>
          <mat-button-toggle value="uncertain">不确定 ({{ uncertainCount() }})</mat-button-toggle>
          <mat-button-toggle value="likely_real">高疑似真实 ({{ likelyRealCount() }})</mat-button-toggle>
          <mat-button-toggle value="high_real">高置信真实 ({{ highRealCount() }})</mat-button-toggle>
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
              </div>
              <div class="card-body">
                @if (task.status === 'completed' && task.overallScore != null) {
                  <div class="score-row">
                    <span class="score-label">生成概率</span>
                    <span class="score-value" [style.color]="getScoreColor(task.overallScore)">
                      {{ (task.overallScore * 100).toFixed(1) }}%
                    </span>
                  </div>
                  <div class="meta-row">
                    <mat-chip [style.backgroundColor]="getRiskBgColor(task.overallScore)">
                      {{ getRiskLabel(task.overallScore) }}
                    </mat-chip>
                    <span class="status-text">{{ getStatusLabel(task.status) }}</span>
                  </div>
                } @else {
                  <div class="score-row">
                    <span class="score-label">状态</span>
                    <span class="status-big">{{ getStatusLabel(task.status) }}</span>
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
export class DetectionListComponent implements OnInit {
  riskFilter: RiskFilter = 'all';
  allTasks = signal<TaskCard[]>([]);

  constructor(
    private mockData: MockDataService,
    private taskService: TaskService,
    private router: Router,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    // 1. 加载真实上传历史
    const cards: TaskCard[] = [];
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      if (raw) {
        const history = JSON.parse(raw);
        for (const r of history) {
          cards.push({
            id: r.taskId,
            fileName: r.fileName,
            fileSize: r.fileSize || 0,
            uploadTime: r.uploadTime || '',
            status: 'pending',
            overallScore: undefined,
            isMock: false,
          });
        }
      }
    } catch { /* ignore */ }

    // 2. 追加 mock 样本数据（用于 demo）
    const uploadedFiles = this.mockData.getUploadedFiles();
    for (const f of uploadedFiles) {
      cards.push({
        ...f,
        isMock: true,
      });
    }

    this.allTasks.set(cards);

    // 3. 对真实任务，异步轮询后端获取最新状态
    for (const card of cards) {
      if (!card.isMock) {
        this.taskService.getTaskStatus(card.id).subscribe({
          next: (status) => {
            const updated = this.allTasks().map(c => {
              if (c.id === card.id) {
                return { ...c, status: status.status, overallScore: c.overallScore };
              }
              return c;
            });
            this.allTasks.set(updated);

            // 如果完成，获取结果中的分数
            if (status.status === 'completed') {
              this.taskService.getTaskResult(card.id).subscribe({
                next: (result) => {
                  const refreshed = this.allTasks().map(c => {
                    if (c.id === card.id) {
                      return {
                        ...c,
                        status: 'completed' as const,
                        overallScore: result.overall_score,
                      };
                    }
                    return c;
                  });
                  this.allTasks.set(refreshed);
                },
                error: () => { /* 结果获取失败，保持当前状态 */ },
              });
            }
          },
          error: () => { /* 后端不可达，保持 pending 状态 */ },
        });
      }
    }
  }

  highCount = computed(() => this.allTasks().filter(t => this.getRisk(t.overallScore) === 'high').length);
  suspectedCount = computed(() => this.allTasks().filter(t => this.getRisk(t.overallScore) === 'suspected').length);
  uncertainCount = computed(() => this.allTasks().filter(t => this.getRisk(t.overallScore) === 'uncertain').length);
  likelyRealCount = computed(() => this.allTasks().filter(t => this.getRisk(t.overallScore) === 'likely_real').length);
  highRealCount = computed(() => this.allTasks().filter(t => this.getRisk(t.overallScore) === 'high_real').length);

  filteredTasks = computed(() => {
    const tasks = this.allTasks();
    if (this.riskFilter === 'all') return tasks;
    return tasks.filter(t => this.getRisk(t.overallScore) === this.riskFilter);
  });

  private getRisk(score?: number): 'high' | 'suspected' | 'uncertain' | 'likely_real' | 'high_real' {
    if (score == null) return 'high_real';
    if (score >= 0.8) return 'high';
    if (score >= 0.5) return 'suspected';
    if (score >= 0.3) return 'uncertain';
    if (score >= 0.1) return 'likely_real';
    return 'high_real';
  }

  getRiskLabel(score?: number): string {
    switch (this.getRisk(score)) {
      case 'high': return '高置信生成';
      case 'suspected': return '高疑似生成';
      case 'uncertain': return '不确定';
      case 'likely_real': return '高疑似真实';
      case 'high_real': return '高置信真实';
    }
  }

  getRiskBgColor(score?: number): string {
    switch (this.getRisk(score)) {
      case 'high': return '#ffcdd2';
      case 'suspected': return '#fff3e0';
      case 'uncertain': return '#fff9c4';
      case 'likely_real': return '#c8e6c9';
      case 'high_real': return '#e8f5e9';
    }
  }

  getScoreColor(score?: number): string {
    if (score == null) return '#9e9e9e';
    if (score >= 0.8) return '#d32f2f';
    if (score >= 0.5) return '#f57c00';
    if (score >= 0.3) return '#f9a825';
    if (score >= 0.1) return '#66bb6a';
    return '#388e3c';
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
