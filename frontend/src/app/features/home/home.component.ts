import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatToolbarModule } from '@angular/material/toolbar';

import { HealthApiService } from '../../core/services/health-api.service';

type ServiceState = 'checking' | 'online' | 'offline';

@Component({
  selector: 'app-home',
  imports: [MatCardModule, MatProgressSpinnerModule, MatToolbarModule],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HomeComponent implements OnInit {
  private readonly healthApi = inject(HealthApiService);

  readonly serviceState = signal<ServiceState>('checking');

  ngOnInit(): void {
    this.healthApi.check().subscribe({
      next: () => this.serviceState.set('online'),
      error: () => this.serviceState.set('offline'),
    });
  }
}
