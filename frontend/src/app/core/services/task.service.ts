import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, timer, switchMap, takeWhile, tap, map, Subject, takeUntil } from 'rxjs';

/**
 * 任务状态响应（对应 /api/tasks/{task_id}）
 */
export interface TaskStatus {
  task_id: string;
  file_name: string;
  file_size: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;       // 0~100
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export type RiskLevel = 'very_low' | 'low' | 'medium' | 'high' | 'very_high';

/** 五级风险中文标签（对应后端 RISK_LEVEL_LABELS） */
export const RISK_LEVEL_LABELS: Record<RiskLevel, string> = {
  very_low: '极低风险',
  low: '低风险',
  medium: '中风险',
  high: '高风险',
  very_high: '极高风险',
};

/** 五级风险背景色（very_high=伪造红色系 → very_low=真实绿色系） */
export const RISK_LEVEL_COLORS: Record<RiskLevel, string> = {
  very_low: '#dcfce7',
  low: '#ecfccb',
  medium: '#fef9c3',
  high: '#ffedd5',
  very_high: '#fee2e2',
};

/** 五级风险文字色（用于分数/强调文字） */
export const RISK_LEVEL_TEXT_COLORS: Record<RiskLevel, string> = {
  very_low: '#15803d',
  low: '#4d7c0f',
  medium: '#a16207',
  high: '#c2410c',
  very_high: '#b91c1c',
};

/** 校准后的五级风险分界阈值（对应后端 RISK_LEVEL_BOUNDARIES） */
const RISK_LEVEL_BOUNDARIES = [0.1186554090, 0.2370573707, 0.4702857587, 0.6720226015];

/** 由检测分数映射到五级风险（校准阈值，权威来源） */
export function riskLevelForScore(score: number | null | undefined): RiskLevel | null {
  if (score == null) return null;
  if (score < RISK_LEVEL_BOUNDARIES[0]) return 'very_low';
  if (score < RISK_LEVEL_BOUNDARIES[1]) return 'low';
  if (score < RISK_LEVEL_BOUNDARIES[2]) return 'medium';
  if (score < RISK_LEVEL_BOUNDARIES[3]) return 'high';
  return 'very_high';
}

/**
 * 检测结果响应（对应 /api/tasks/{task_id}/result）
 */
export interface TaskResult {
  task_id: string;
  filename: string;
  original_image_url: string;
  mask_available: boolean;
  mask_image_url: string | null;
  localization_message: string | null;
  overall_score: number;        // 兼容字段，等同于 score_generated
  score_generated: number;
  score_semantics: 'uncalibrated_sigmoid_risk_score';
  prediction: 'generated' | 'original';
  threshold: number;
  risk_level: RiskLevel;
  risk_level_semantics: 'experimental_class_balanced_calibrated_risk';
  risk_level_version: 'experimental-platt-balanced-v1';
  risk_level_is_experimental: true;
  model_version: string;
  weight_sha256: string;
  device: string;
  processing_time: number;      // 秒
  suspect_regions: {
    id: number;
    label: string;
    confidence: number;
    bbox: { x: number; y: number; width: number; height: number };
    description: string;
  }[];
  model_probabilities: {
    model: string;
    probability: number;
  }[];
}

/**
 * TaskService — 任务状态轮询与结果获取
 *
 * 核心流程：
 * 1. 上传文件 → 拿到 task_id
 * 2. 轮询 /api/tasks/{task_id} 直到 status 为 completed 或 failed
 * 3. 完成后获取 /api/tasks/{task_id}/result
 */
@Injectable({ providedIn: 'root' })
export class TaskService {
  /** 轮询间隔（毫秒） */
  private readonly POLL_INTERVAL = 3000;

  constructor(private http: HttpClient) {}

  /**
   * 获取任务当前状态
   */
  getTaskStatus(taskId: string): Observable<TaskStatus> {
    return this.http.get<TaskStatus>(`/api/tasks/${taskId}`);
  }

  /**
   * 轮询任务状态直到完成或失败
   * @param taskId 任务ID
   * @param stop$ 外部可通过发出信号取消轮询（如组件销毁时）
   * @returns 每次轮询发出最新状态，complete 时结束
   */
  pollTaskStatus(taskId: string, stop$?: Subject<void>): Observable<TaskStatus> {
    const poll$ = timer(0, this.POLL_INTERVAL).pipe(
      switchMap(() => this.getTaskStatus(taskId)),
      takeWhile(
        (status) => status.status !== 'completed' && status.status !== 'failed',
        true // 包含最后一次（completed/failed）
      ),
    );

    return stop$ ? poll$.pipe(takeUntil(stop$)) : poll$;
  }

  /**
   * 获取任务检测结果
   */
  getTaskResult(taskId: string): Observable<TaskResult> {
    return this.http.get<TaskResult>(`/api/tasks/${taskId}/result`);
  }

  /**
   * 便捷方法：轮询直到完成，然后自动获取结果
   */
  waitForResult(taskId: string, stop$?: Subject<void>): Observable<TaskResult> {
    return this.pollTaskStatus(taskId, stop$).pipe(
      // 只在 completed 时继续取结果
      takeWhile((status) => status.status !== 'failed', true),
      switchMap((status) => {
        if (status.status === 'completed') {
          return this.getTaskResult(taskId);
        }
        // 未完成或失败时不发出结果
        return new Observable<TaskResult>(() => {});
      }),
    );
  }
}
