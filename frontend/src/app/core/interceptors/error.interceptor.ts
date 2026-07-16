import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

/**
 * 全局错误拦截器
 * - 401 未授权 → 自动跳转登录页
 * - 其他错误 → 统一格式化后继续抛出，让具体组件处理
 */
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);

  return next(req).pipe(
    catchError((error) => {
      if (error.status === 401) {
        localStorage.removeItem('forensic_token');
        router.navigate(['/login']);
      }
      return throwError(() => error);
    })
  );
};
