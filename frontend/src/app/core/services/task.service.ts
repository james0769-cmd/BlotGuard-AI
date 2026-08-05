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
  risk_level: null;
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
