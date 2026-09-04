import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

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
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/workspace/workspace.component').then((m) => m.WorkspaceComponent),
  },
  {
    path: 'gallery',
    loadComponent: () =>
      import('./features/gallery/gallery.component').then((m) => m.GalleryComponent),
  },
  {
    path: 'reports',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/reports/reports.component').then(
        (m) => m.ReportsComponent
      ),
  },
  {
    path: 'detection',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/detection-list/detection-list.component').then(
        (m) => m.DetectionListComponent
      ),
  },
  {
    path: 'detection/:taskId',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/detection-detail/detection-detail.component').then(
        (m) => m.DetectionDetailComponent
      ),
  },
  {
    path: 'queue',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./queue/queue.component').then((m) => m.QueueComponent),
  },
  {
    // 通配符路由：未匹配的路径重定向到工作台
    path: '**',
    redirectTo: '/workspace',
  },
];
