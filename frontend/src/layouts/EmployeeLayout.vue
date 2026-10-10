<template>
  <el-container class="app-shell employee-shell">
    <el-aside :width="app.sidebarWidth" class="side-nav">
      <div class="brand">
        <div class="brand-mark">HR</div>
        <div class="brand-copy"><strong>HR AI System</strong><span>员工自助服务</span></div>
      </div>
      <el-menu :default-active="$route.path" router class="nav-menu">
        <el-menu-item index="/employee/home"
          ><el-icon><DataAnalysis /></el-icon><template #title>员工工作台</template></el-menu-item
        >
        <el-menu-item index="/employee/attendance"
          ><el-icon><Calendar /></el-icon><template #title>我的考勤</template></el-menu-item
        >
        <el-menu-item index="/employee/leaves"
          ><el-icon><Document /></el-icon><template #title>我的请假</template></el-menu-item
        >
        <el-menu-item index="/employee/salary"
          ><el-icon><Money /></el-icon><template #title>我的工资条</template></el-menu-item
        >
        <el-menu-item index="/employee/profile"
          ><el-icon><User /></el-icon><template #title>我的档案</template></el-menu-item
        >
        <el-menu-item index="/employee/messages"
          ><el-icon><Bell /></el-icon><template #title>我的消息</template></el-menu-item
        >
        <el-menu-item index="/employee/agent"
          ><el-icon><ChatDotRound /></el-icon><template #title>智能助手</template></el-menu-item
        >
      </el-menu>
    </el-aside>
    <el-container class="main-container"
      ><el-header class="topbar"
        ><div class="topbar-left">
          <el-button text @click="app.toggleSidebar"
            ><el-icon><Fold /></el-icon></el-button
          ><span class="breadcrumb">{{ $route.meta.title }}</span>
        </div>
        <div class="topbar-right">
          <span class="portal-label">员工自助端</span
          ><el-dropdown @command="command"
            ><el-button text
              ><el-avatar :size="30">我</el-avatar><el-icon><ArrowDown /></el-icon></el-button
            ><template #dropdown
              ><el-dropdown-menu
                ><el-dropdown-item v-if="auth.isAdmin" command="admin">返回管理端</el-dropdown-item
                ><el-dropdown-item command="password">修改密码</el-dropdown-item
                ><el-dropdown-item divided command="logout"
                  >退出登录</el-dropdown-item
                ></el-dropdown-menu
              ></template
            ></el-dropdown
          >
        </div></el-header
      ><el-main class="content-area"><router-view /></el-main
    ></el-container>
  </el-container>
</template>
<script setup>
import { useRouter } from 'vue-router'
import {
  ArrowDown,
  Bell,
  Calendar,
  ChatDotRound,
  DataAnalysis,
  Document,
  Fold,
  Money,
  User,
} from '@element-plus/icons-vue'
import { useAppStore } from '../stores/app'
import { useAuthStore } from '../stores/auth'
const app = useAppStore()
const auth = useAuthStore()
const router = useRouter()
async function command(value) {
  if (value === 'admin') return router.push('/dashboard')
  if (value === 'password') return router.push('/change-password')
  if (value === 'logout') {
    await auth.logout()
    router.replace('/login')
  }
}
</script>
