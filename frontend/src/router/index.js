import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/change-password',
    component: () => import('../views/ChangePasswordView.vue'),
    meta: { title: '修改密码' },
  },
  {
    path: '/',
    component: () => import('../layouts/AppLayout.vue'),
    meta: { admin: true },
    children: [
      { path: '', redirect: '/dashboard' },
      {
        path: 'dashboard',
        component: () => import('../views/DashboardView.vue'),
        meta: { title: '工作台', admin: true },
      },
      {
        path: 'departments',
        component: () => import('../views/DepartmentView.vue'),
        meta: { title: '部门管理', admin: true },
      },
      {
        path: 'positions',
        component: () => import('../views/PositionView.vue'),
        meta: { title: '岗位管理', admin: true },
      },
      {
        path: 'employees',
        component: () => import('../views/EmployeeView.vue'),
        meta: { title: '员工档案', admin: true },
      },
      {
        path: 'accounts',
        component: () => import('../views/AccountView.vue'),
        meta: { title: '账号管理', admin: true },
      },
      {
        path: 'attendance',
        component: () => import('../views/AttendanceView.vue'),
        meta: { title: '考勤管理', admin: true },
      },
      {
        path: 'leaves',
        component: () => import('../views/LeaveApprovalView.vue'),
        meta: { title: '请假审批', admin: true },
      },
      {
        path: 'payroll',
        component: () => import('../views/SalaryView.vue'),
        meta: { title: '薪酬管理', admin: true },
      },
      {
        path: 'messages',
        component: () => import('../views/MessageView.vue'),
        meta: { title: '消息中心', admin: true },
      },
    ],
  },
  {
    path: '/employee',
    component: () => import('../layouts/EmployeeLayout.vue'),
    meta: { employee: true },
    children: [
      { path: '', redirect: '/employee/home' },
      {
        path: 'home',
        component: () => import('../views/employee/EmployeeHomeView.vue'),
        meta: { title: '员工工作台', employee: true },
      },
      {
        path: 'attendance',
        component: () => import('../views/employee/MyAttendanceView.vue'),
        meta: { title: '我的考勤', employee: true },
      },
      {
        path: 'leaves',
        component: () => import('../views/employee/MyLeaveView.vue'),
        meta: { title: '我的请假', employee: true },
      },
      {
        path: 'salary',
        component: () => import('../views/employee/MySalaryView.vue'),
        meta: { title: '我的工资条', employee: true },
      },
      {
        path: 'profile',
        component: () => import('../views/employee/MyProfileView.vue'),
        meta: { title: '我的档案', employee: true },
      },
      {
        path: 'messages',
        component: () => import('../views/employee/MyMessagesView.vue'),
        meta: { title: '我的消息', employee: true },
      },
      {
        path: 'agent',
        component: () => import('../views/employee/EmployeeAgentView.vue'),
        meta: { title: '智能助手', employee: true },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({ history: createWebHistory(), routes })
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) return auth.isAuthenticated ? '/dashboard' : true
  if (!auth.isAuthenticated) return `/login?redirect=${encodeURIComponent(to.fullPath)}`
  if (!auth.user) {
    try {
      await auth.loadMe()
    } catch {
      return '/login'
    }
  }
  if (auth.user?.must_change_password && to.path !== '/change-password') return '/change-password'
  if (to.meta.admin && !auth.isAdmin)
    return auth.user?.role === 'EMPLOYEE' ? '/employee/home' : '/change-password'
  if (to.meta.employee && !auth.user?.employee_id)
    return auth.isAdmin ? '/dashboard' : '/change-password'
  return true
})

export default router
