import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatToolbarModule } from '@angular/material/toolbar';

import {
  DetectionApiService,
  DetectionResponse,
} from '../../core/services/detection-api.service';
import { HealthApiService } from '../../core/services/health-api.service';

type ServiceState = 'checking' | 'online' | 'offline';

@Component({
  selector: 'app-home',
  imports: [
    MatButtonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatToolbarModule,
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HomeComponent implements OnInit {
  private readonly healthApi = inject(HealthApiService);
  private readonly detectionApi = inject(DetectionApiService);

  readonly serviceState = signal<ServiceState>('checking');
  readonly selectedFile = signal<File | null>(null);
  readonly detecting = signal(false);
  readonly detection = signal<DetectionResponse | null>(null);
  readonly detectionError = signal('');

  ngOnInit(): void {
    this.healthApi.check().subscribe({
      next: () => this.serviceState.set('online'),
      error: () => this.serviceState.set('offline'),
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedFile.set(input.files?.[0] ?? null);
    this.detection.set(null);
    this.detectionError.set('');
  }

  runDetection(): void {
    const image = this.selectedFile();
    if (!image) return;

    this.detecting.set(true);
    this.detection.set(null);
    this.detectionError.set('');
    this.detectionApi.detect(image).subscribe({
      next: (result) => {
        this.detection.set(result);
        this.detecting.set(false);
      },
      error: () => {
        this.detectionError.set('检测失败，请确认后端模型服务已启动。');
        this.detecting.set(false);
      },
    });
  }
}
