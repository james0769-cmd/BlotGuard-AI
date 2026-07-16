import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/workspace',
    pathMatch: 'full',
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./features/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'workspace',
    loadComponent: () =>
      import('./features/workspace/workspace.component').then((m) => m.WorkspaceComponent),
  },
  {
    path: 'detection/:taskId',
    loadComponent: () =>
      import('./features/detection-detail/detection-detail.component').then(
        (m) => m.DetectionDetailComponent
      ),
  },
  {
    // 通配符路由：未匹配的路径重定向到工作台
    path: '**',
    redirectTo: '/workspace',
  },
];
