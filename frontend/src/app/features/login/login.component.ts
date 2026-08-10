import { Component, signal } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
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
    MatTabsModule,
  ],
  template: `
    <div class="login-wrapper">
      <mat-card class="login-card">
        <mat-tab-group
          [selectedIndex]="activeTab()"
          (selectedIndexChange)="onTabChange($event)"
          animationDuration="300ms"
          class="auth-tabs">

          <!-- ========== 登录 Tab ========== -->
          <mat-tab label="登录">
            <div class="tab-content">
              <p class="tab-hint">使用已有账号登录</p>

              <mat-form-field appearance="outline" class="full-width">
                <mat-label>用户名</mat-label>
                <input matInput [(ngModel)]="username" placeholder="请输入用户名" />
                <mat-icon matSuffix>person</mat-icon>
              </mat-form-field>

              <mat-form-field appearance="outline" class="full-width">
                <mat-label>密码</mat-label>
                <input matInput [(ngModel)]="password"
                       [type]="hidePassword() ? 'password' : 'text'"
                       placeholder="请输入密码" />
                <button mat-icon-button matSuffix (click)="hidePassword.set(!hidePassword())"
                        type="button" tabindex="-1">
                  <mat-icon>{{ hidePassword() ? 'visibility_off' : 'visibility' }}</mat-icon>
                </button>
              </mat-form-field>

              @if (errorMsg()) {
                <p class="error-msg">{{ errorMsg() }}</p>
              }

              <button mat-raised-button color="primary" class="full-width"
                      (click)="onLogin()" [disabled]="loading()">
                @if (loading()) {
                  <mat-spinner diameter="20"></mat-spinner>
                } @else {
                  登录
                }
              </button>

              <p class="switch-hint">
                还没有账号？
                <a (click)="activeTab.set(1)" class="switch-link">立即注册</a>
              </p>
            </div>
          </mat-tab>

          <!-- ========== 注册 Tab ========== -->
          <mat-tab label="注册">
            <div class="tab-content">
              <p class="tab-hint">创建新账号以使用系统</p>

              <mat-form-field appearance="outline" class="full-width">
                <mat-label>用户名</mat-label>
                <input matInput [(ngModel)]="regUsername" placeholder="请输入用户名（3-20个字符）" />
                <mat-icon matSuffix>person_add</mat-icon>
              </mat-form-field>

              <mat-form-field appearance="outline" class="full-width">
                <mat-label>密码</mat-label>
                <input matInput [(ngModel)]="regPassword"
                       [type]="hideRegPassword() ? 'password' : 'text'"
                       placeholder="请输入密码（至少6位）" />
                <button mat-icon-button matSuffix (click)="hideRegPassword.set(!hideRegPassword())"
                        type="button" tabindex="-1">
                  <mat-icon>{{ hideRegPassword() ? 'visibility_off' : 'visibility' }}</mat-icon>
                </button>
              </mat-form-field>

              <mat-form-field appearance="outline" class="full-width">
                <mat-label>确认密码</mat-label>
                <input matInput [(ngModel)]="regConfirmPassword"
                       [type]="hideRegPassword() ? 'password' : 'text'"
                       placeholder="请再次输入密码" />
                <mat-icon matSuffix>lock</mat-icon>
              </mat-form-field>

              @if (regErrorMsg()) {
                <p class="error-msg">{{ regErrorMsg() }}</p>
              }
              @if (regSuccessMsg()) {
                <p class="success-msg">{{ regSuccessMsg() }}</p>
              }

              <button mat-raised-button color="primary" class="full-width"
                      (click)="onRegister()" [disabled]="regLoading()">
                @if (regLoading()) {
                  <mat-spinner diameter="20"></mat-spinner>
                } @else {
                  注册
                }
              </button>

              <p class="switch-hint">
                已有账号？
                <a (click)="activeTab.set(0)" class="switch-link">返回登录</a>
              </p>
            </div>
          </mat-tab>

        </mat-tab-group>
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
      max-width: 440px;
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    .auth-tabs {
      padding: 0 28px 24px;
    }
    .tab-content {
      padding-top: 20px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .tab-hint {
      color: #6b7280;
      font-size: 0.85rem;
      margin: 0 0 8px;
    }
    .full-width {
      width: 100%;
    }
    .error-msg {
      color: #ef4444;
      font-size: 0.85rem;
      margin: 4px 0;
      padding: 6px 10px;
      background: #fef2f2;
      border-radius: 6px;
    }
    .success-msg {
      color: #16a34a;
      font-size: 0.85rem;
      margin: 4px 0;
      padding: 6px 10px;
      background: #f0fdf4;
      border-radius: 6px;
    }
    .switch-hint {
      text-align: center;
      font-size: 0.85rem;
      color: #6b7280;
      margin: 12px 0 0;
    }
    .switch-link {
      color: #1976d2;
      cursor: pointer;
      text-decoration: none;
      font-weight: 500;
    }
    .switch-link:hover {
      text-decoration: underline;
    }
    button[mat-raised-button] {
      height: 44px;
      font-size: 0.95rem;
      font-weight: 500;
      border-radius: 10px;
      margin-top: 8px;
    }
  `],
})
export class LoginComponent {
  // --- 共用的 loading & tab 状态 ---
  activeTab = signal(0);

  // --- 登录表单 ---
  username = '';
  password = '';
  hidePassword = signal(true);
  loading = signal(false);
  errorMsg = signal('');

  // --- 注册表单 ---
  regUsername = '';
  regPassword = '';
  regConfirmPassword = '';
  hideRegPassword = signal(true);
  regLoading = signal(false);
  regErrorMsg = signal('');
  regSuccessMsg = signal('');

  constructor(
    private authService: AuthService,
    private router: Router,
  ) {}

  /** Tab 切换时清空错误提示 */
  onTabChange(index: number): void {
    this.activeTab.set(index);
    this.errorMsg.set('');
    this.regErrorMsg.set('');
    this.regSuccessMsg.set('');
  }

  // ==================== 登录逻辑 ====================

  onLogin(): void {
    if (!this.username.trim() || !this.password) {
      this.errorMsg.set('请输入用户名和密码');
      return;
    }

    this.loading.set(true);
    this.errorMsg.set('');

    this.authService.login({ username: this.username.trim(), password: this.password }).subscribe({
      next: () => {
        this.loading.set(false);
        this.router.navigate(['/workspace']);
      },
      error: (err) => {
        this.loading.set(false);
        this.errorMsg.set(err?.error?.message || '登录失败，请检查网络连接');
      },
    });
  }

  // ==================== 注册逻辑 ====================

  onRegister(): void {
    const user = this.regUsername.trim();
    const pwd = this.regPassword;
    const confirm = this.regConfirmPassword;

    // --- 前端校验 ---
    if (!user) {
      this.regErrorMsg.set('请输入用户名');
      return;
    }
    if (user.length < 3 || user.length > 20) {
      this.regErrorMsg.set('用户名长度需在 3-20 个字符之间');
      return;
    }
    if (!/^[a-zA-Z0-9_一-龥]+$/.test(user)) {
      this.regErrorMsg.set('用户名只能包含字母、数字、下划线或中文');
      return;
    }
    if (!pwd) {
      this.regErrorMsg.set('请输入密码');
      return;
    }
    if (pwd.length < 6) {
      this.regErrorMsg.set('密码长度不能少于 6 位');
      return;
    }
    if (pwd !== confirm) {
      this.regErrorMsg.set('两次输入的密码不一致');
      return;
    }

    this.regLoading.set(true);
    this.regErrorMsg.set('');
    this.regSuccessMsg.set('');

    // 注册成功后调用登录接口（后端 mock 模式接受任意账号密码）
    this.authService.login({ username: user, password: pwd }).subscribe({
      next: () => {
        this.regSuccessMsg.set('注册成功，即将跳转...');
        // 延迟跳转让用户看到成功提示
        setTimeout(() => {
          this.regLoading.set(false);
          this.router.navigate(['/workspace']);
        }, 800);
      },
      error: (err) => {
        this.regLoading.set(false);
        this.regErrorMsg.set(err?.error?.message || '注册失败，请检查网络连接');
      },
    });
  }
}
