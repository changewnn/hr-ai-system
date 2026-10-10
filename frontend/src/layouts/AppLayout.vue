<template>
  <el-container class="app-shell">
    <el-aside :width="app.sidebarWidth" class="side-nav">
      <div class="brand" :class="{ compact: app.sidebarCollapsed }">
        <div class="brand-mark">HR</div>
        <div v-if="!app.sidebarCollapsed" class="brand-copy">
          <strong>HR AI System</strong>
          <span>轻量人事管理</span>
        </div>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        :collapse="app.sidebarCollapsed"
        class="nav-menu"
      >
        <el-menu-item index="/dashboard"
          ><el-icon><DataAnalysis /></el-icon><template #title>工作台</template></el-menu-item
        >
        <el-menu-item index="/departments"
          ><el-icon><OfficeBuilding /></el-icon><template #title>部门管理</template></el-menu-item
        >
        <el-menu-item index="/positions"
          ><el-icon><Briefcase /></el-icon><template #title>岗位管理</template></el-menu-item
        >
        <el-menu-item index="/employees"
          ><el-icon><User /></el-icon><template #title>员工档案</template></el-menu-item
        >
        <el-menu-item index="/accounts"
          ><el-icon><Key /></el-icon><template #title>账号管理</template></el-menu-item
        >
        <el-menu-item index="/attendance"
          ><el-icon><Calendar /></el-icon><template #title>考勤管理</template></el-menu-item
        >
        <el-menu-item index="/leaves"
          ><el-icon><DocumentChecked /></el-icon><template #title>请假审批</template></el-menu-item
        >
        <el-menu-item index="/payroll"
          ><el-icon><Money /></el-icon><template #title>薪酬管理</template></el-menu-item
        >
        <el-menu-item index="/messages"
          ><el-icon><Bell /></el-icon><template #title>消息中心</template></el-menu-item
        >
      </el-menu>
      <div v-if="!app.sidebarCollapsed" class="side-footer">MVP · v0.1.0</div>
    </el-aside>
    <el-container class="main-container">
      <el-header class="topbar">
        <div class="topbar-left">
          <el-button text @click="app.toggleSidebar"
            ><el-icon size="20"
              ><Fold v-if="!app.sidebarCollapsed" /><Expand v-else /></el-icon></el-button
          ><span class="breadcrumb">{{ $route.meta.title || '工作台' }}</span>
        </div>
        <div class="topbar-right">
          <el-badge :value="app.unreadMessages" class="message-badge"
            ><el-button text circle
              ><el-icon size="19"><Bell /></el-icon></el-button
          ></el-badge>
          <el-divider direction="vertical" />
          <el-avatar :size="32" class="user-avatar">HR</el-avatar>
          <div class="user-meta">
            <strong>{{ auth.user?.username || app.displayName }}</strong
            ><span>{{ auth.user?.role || app.roleLabel }}</span>
          </div>
          <el-dropdown @command="handleCommand"
            ><el-button text
              ><el-icon><ArrowDown /></el-icon></el-button
            ><template #dropdown
              ><el-dropdown-menu
                ><el-dropdown-item v-if="auth.canUseEmployeePortal" command="employee"
                  >员工自助端</el-dropdown-item
                ><el-dropdown-item command="password">修改密码</el-dropdown-item
                ><el-dropdown-item divided command="logout"
                  >退出登录</el-dropdown-item
                ></el-dropdown-menu
              ></template
            ></el-dropdown
          >
        </div>
      </el-header>
      <el-main class="content-area"><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useAppStore } from '../stores/app'
import { useRouter } from 'vue-router'
import {
  ArrowDown,
  Bell,
  Briefcase,
  Calendar,
  DataAnalysis,
  DocumentChecked,
  Expand,
  Fold,
  Key,
  Money,
  OfficeBuilding,
  User,
} from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const app = useAppStore()
const auth = useAuthStore()
const router = useRouter()
async function handleCommand(command) {
  if (command === 'employee') return router.push('/employee/home')
  if (command === 'password') return router.push('/change-password')
  if (command === 'logout') {
    await auth.logout()
    router.replace('/login')
  }
}
</script>
