import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('../layouts/AppLayout.vue'),
      children: [
        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { title: '工作台' } },
        { path: 'employees', component: () => import('../views/ComingSoonView.vue'), meta: { title: '员工档案' } },
        { path: 'attendance', component: () => import('../views/ComingSoonView.vue'), meta: { title: '考勤管理' } },
        { path: 'leaves', component: () => import('../views/ComingSoonView.vue'), meta: { title: '请假审批' } },
        { path: 'payroll', component: () => import('../views/ComingSoonView.vue'), meta: { title: '薪酬管理' } },
        { path: 'messages', component: () => import('../views/ComingSoonView.vue'), meta: { title: '消息中心' } },
      ],
    },
  ],
})

export default router
