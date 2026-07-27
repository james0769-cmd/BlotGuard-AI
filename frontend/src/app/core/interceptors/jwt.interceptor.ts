import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';

/**
 * JWT 拦截器（函数式写法，Angular 15+ 推荐）
 *
 * 工作原理：每次发 HTTP 请求时，自动检查本地是否有 token，
 * 如果有，就在请求头加上 Authorization: Bearer xxx
 * 后端收到后就知道"这是谁在请求"
 */
export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const token = authService.getToken();

  if (token) {
    // 克隆请求并加上 Authorization 头
    const cloned = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`,
      },
    });
    return next(cloned);
  }

  return next(req);
};
