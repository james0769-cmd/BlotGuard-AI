import { Component, signal } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  imports: [
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="login-wrapper">
      <mat-card class="login-card">
        <mat-card-header>
          <mat-card-title>登录</mat-card-title>
          <mat-card-subtitle>图像鉴伪检测系统</mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>用户名</mat-label>
            <input matInput [(ngModel)]="username" placeholder="请输入用户名" />
            <mat-icon matSuffix>person</mat-icon>
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>密码</mat-label>
            <input matInput [(ngModel)]="password" [type]="hidePassword() ? 'password' : 'text'" placeholder="请输入密码" />
            <button mat-icon-button matSuffix (click)="hidePassword.set(!hidePassword())">
              <mat-icon>{{ hidePassword() ? 'visibility_off' : 'visibility' }}</mat-icon>
            </button>
          </mat-form-field>

          @if (errorMsg()) {
            <p class="error-msg">{{ errorMsg() }}</p>
          }
        </mat-card-content>
        <mat-card-actions>
          <button mat-raised-button color="primary" class="full-width" (click)="onLogin()" [disabled]="loading()">
            @if (loading()) {
              <mat-spinner diameter="20"></mat-spinner>
            } @else {
              登录
            }
          </button>
        </mat-card-actions>
      </mat-card>
    </div>
  `,
  styles: [`
    .login-wrapper {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 80vh;
      background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
      animation: fadeIn 0.5s ease-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(16px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .login-card {
      width: 100%;
      max-width: 400px;
      padding: 32px 28px;
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    .full-width {
      width: 100%;
    }
    .error-msg {
      color: #ef4444;
      font-size: 0.85rem;
      margin-top: 4px;
      padding: 6px 10px;
      background: #fef2f2;
      border-radius: 6px;
    }
    mat-card-header {
      margin-bottom: 8px;
    }
    mat-card-actions {
      padding: 16px 0 0;
    }
    mat-card-actions button {
      height: 44px;
      font-size: 0.95rem;
      font-weight: 500;
      border-radius: 10px;
    }
  `],
})
export class LoginComponent {
  username = '';
  password = '';
  hidePassword = signal(true);
  loading = signal(false);
  errorMsg = signal('');

  constructor(
    private authService: AuthService,
    private router: Router,
  ) {}

  onLogin(): void {
    if (!this.username || !this.password) {
      this.errorMsg.set('请输入用户名和密码');
      return;
    }

    this.loading.set(true);
    this.errorMsg.set('');

    this.authService.login({ username: this.username, password: this.password }).subscribe({
      next: () => {
        this.loading.set(false);
        this.router.navigate(['/workspace']);
      },
      error: (err) => {
        this.loading.set(false);
        this.errorMsg.set(err?.error?.message || '登录失败，请检查用户名和密码');
      },
    });
  }
}
