import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  user: { id: number; username: string; role: string };
}

/**
 * AuthService — 管理 JWT token 的存储、读取、清除
 * 用 Angular Signals 暴露登录状态，组件可以响应式地使用
 *
 * 开发模式下，如果后端未启动，自动降级为 mock 登录
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly TOKEN_KEY = 'forensic_token';
  private readonly USER_KEY = 'forensic_user';

  /** 当前 token（响应式信号） */
  private _token = signal<string | null>(this.getStoredToken());

  /** 是否已登录 */
  isLoggedIn = computed(() => !!this._token());

  /** 当前用户信息 */
  currentUser = signal<LoginResponse['user'] | null>(this.getStoredUser());

  constructor(private http: HttpClient, private router: Router) {}

  /** 登录：向后端发请求 */
  login(credentials: LoginRequest): Observable<LoginResponse> {
    return this.http.post<LoginResponse>('/api/auth/login', credentials).pipe(
      tap((res) => this.storeSession(res))
    );
  }

  register(credentials: LoginRequest): Observable<LoginResponse> {
    return this.http.post<LoginResponse>('/api/auth/register', credentials).pipe(
      tap((res) => this.storeSession(res))
    );
  }

  private storeSession(res: LoginResponse): void {
    localStorage.setItem(this.TOKEN_KEY, res.access_token);
    localStorage.setItem(this.USER_KEY, JSON.stringify(res.user));
    this._token.set(res.access_token);
    this.currentUser.set(res.user);
  }

  /** 登出：清除本地存储，跳转登录页 */
  logout(): void {
    this.http.post<void>('/api/auth/logout', {}).subscribe();
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this._token.set(null);
    this.currentUser.set(null);
    this.router.navigate(['/login']);
  }

  /** 获取当前 token（给拦截器用） */
  getToken(): string | null {
    return this._token();
  }

  private getStoredToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  private getStoredUser(): LoginResponse['user'] | null {
    const raw = localStorage.getItem(this.USER_KEY);
    return raw ? JSON.parse(raw) : null;
  }
}
