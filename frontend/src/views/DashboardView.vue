<template>
  <div class="dashboard-page">
    <div class="page-heading"><div><p class="eyebrow">OVERVIEW</p><h1>工作台</h1><p class="page-subtitle">掌握团队人事状态，快速处理今日待办。</p></div><el-button type="primary" :icon="Refresh" :loading="loading" @click="checkHealth">刷新状态</el-button></div>
    <el-alert v-if="healthError" type="warning" :closable="false" show-icon class="health-alert" title="后端服务暂不可用，当前展示演示数据" />
    <div class="stat-grid">
      <div v-for="stat in stats" :key="stat.label" class="stat-card"><div class="stat-icon" :class="stat.tone"><el-icon size="21"><component :is="stat.icon" /></el-icon></div><div><span class="stat-label">{{ stat.label }}</span><strong>{{ stat.value }}</strong><small :class="stat.trendClass">{{ stat.trend }}</small></div></div>
    </div>
    <div class="dashboard-grid">
      <section class="panel attendance-panel"><div class="panel-heading"><div><h2>本月考勤概览</h2><span>2026 年 10 月</span></div><el-button text type="primary">查看详情 <el-icon><ArrowRight /></el-icon></el-button></div><div class="attendance-summary"><div class="ring"><div><strong>96.8%</strong><span>平均出勤率</span></div></div><div class="legend"><div><i class="dot green"></i><span>正常出勤</span><strong>86 人</strong></div><div><i class="dot amber"></i><span>迟到 / 早退</span><strong>8 人</strong></div><div><i class="dot red"></i><span>缺卡 / 缺勤</span><strong>2 人</strong></div></div></div></section>
      <section class="panel todo-panel"><div class="panel-heading"><div><h2>待处理事项</h2><span>需要你关注的工作</span></div><el-button text type="primary">全部查看</el-button></div><div class="todo-list"><div v-for="todo in todos" :key="todo.title" class="todo-item"><div class="todo-marker" :class="todo.tone"></div><div class="todo-content"><strong>{{ todo.title }}</strong><span>{{ todo.detail }}</span></div><el-icon class="todo-arrow"><ArrowRight /></el-icon></div></div></section>
    </div>
    <section class="panel activity-panel"><div class="panel-heading"><div><h2>最近动态</h2><span>系统内最新操作记录</span></div><el-button text type="primary">查看日志</el-button></div><el-table :data="activities" style="width: 100%" :show-header="true"><el-table-column prop="action" label="操作" min-width="220" /><el-table-column prop="actor" label="操作人" width="150" /><el-table-column prop="time" label="时间" width="180" /><el-table-column label="状态" width="120"><template #default="{ row }"><el-tag :type="row.type" effect="light" size="small">{{ row.status }}</el-tag></template></el-table-column></el-table></section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ArrowRight, Calendar, CircleCheck, Clock, DocumentChecked, Refresh, User } from '@element-plus/icons-vue'
import { getHealth } from '../api/http'
import { attendanceApi, employeeApi, leaveApi, messageApi } from '../api'

const loading = ref(false)
const healthError = ref(false)
const stats = [
  { label: '在职员工', value: '0', trend: '来自员工档案', trendClass: 'positive', tone: 'blue', icon: User },
  { label: '本月出勤', value: '0', trend: '来自考勤汇总', trendClass: 'positive', tone: 'green', icon: CircleCheck },
  { label: '待审批请假', value: '0', trend: '需要及时处理', trendClass: 'warning', tone: 'amber', icon: DocumentChecked },
  { label: '未读消息', value: '0', trend: '来自消息中心', trendClass: 'positive', tone: 'red', icon: Clock },
]
const todos = [
  { title: '请假审批待处理', detail: '6 条申请等待你的审批', tone: 'amber' },
  { title: '月度薪酬待核对', detail: '2026 年 9 月工资条草稿已生成', tone: 'blue' },
  { title: '考勤异常提醒', detail: '12 条记录需要关注', tone: 'red' },
]
const activities = [
  { action: '发布 2026 年 9 月工资条', actor: 'HR 管理员', time: '今天 09:32', status: '已完成', type: 'success' },
  { action: '新增员工档案：林晓曼', actor: 'HR 管理员', time: '昨天 16:20', status: '已完成', type: 'success' },
  { action: '调整考勤记录 3 条', actor: '张伟', time: '昨天 14:08', status: '已完成', type: 'info' },
]

async function checkHealth() {
  loading.value = true
  healthError.value = false
  try {
    const month = new Date().toISOString().slice(0, 7)
    const [health, employees, attendance, leaves, messages] = await Promise.all([
      getHealth(),
      employeeApi.list({ status: 'ACTIVE', page: 1, page_size: 1 }),
      attendanceApi.summary({ month }),
      leaveApi.pending(),
      messageApi.list({ unread_only: true }),
    ])
    if (health.data?.status !== 'healthy') throw new Error('health check failed')
    stats[0].value = String(employees.data?.total || 0)
    stats[1].value = String((attendance.data || []).reduce((total, item) => total + (item.attendance_days || 0), 0))
    stats[2].value = String((leaves.data || []).length)
    stats[3].value = String(messages.data?.unread_count || 0)
    todos[0].detail = `${stats[2].value} 条申请等待你的审批`
  } catch {
    healthError.value = true
  } finally {
    loading.value = false
  }
}
onMounted(checkHealth)
</script>
