<template>
  <div class="dashboard-page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">OVERVIEW</p>
        <h1>工作台</h1>
        <p class="page-subtitle">掌握团队人事状态，快速处理今日待办。</p>
      </div>
      <el-button type="primary" :icon="Refresh" :loading="loading" @click="checkHealth"
        >刷新状态</el-button
      >
    </div>
    <el-alert
      v-if="healthError"
      type="warning"
      :closable="false"
      show-icon
      class="health-alert"
      title="后端服务暂不可用，无法加载实时数据"
    />
    <div class="stat-grid">
      <div v-for="stat in stats" :key="stat.label" class="stat-card">
        <div class="stat-icon" :class="stat.tone">
          <el-icon size="21"><component :is="stat.icon" /></el-icon>
        </div>
        <div>
          <span class="stat-label">{{ stat.label }}</span
          ><strong>{{ stat.value }}</strong
          ><small :class="stat.trendClass">{{ stat.trend }}</small>
        </div>
      </div>
    </div>
    <div class="dashboard-grid">
      <section class="panel attendance-panel">
        <div class="panel-heading">
          <div>
            <h2>本月考勤概览</h2>
            <span>{{ monthLabel }}</span>
          </div>
          <el-button text type="primary"
            >查看详情 <el-icon><ArrowRight /></el-icon
          ></el-button>
        </div>
        <div class="attendance-summary">
          <div
            class="ring"
            :style="{
              background: `conic-gradient(#4a91ef 0 ${attendanceRate}%, #e9eef5 ${attendanceRate}% 100%)`,
            }"
          >
            <div>
              <strong>{{ attendanceRate }}%</strong><span>平均出勤率</span>
            </div>
          </div>
          <div class="legend">
            <div>
              <i class="dot green"></i><span>正常出勤</span
              ><strong>{{ normalAttendance }} 次</strong>
            </div>
            <div>
              <i class="dot amber"></i><span>迟到 / 早退</span
              ><strong>{{ attendanceExceptions }} 次</strong>
            </div>
            <div>
              <i class="dot red"></i><span>缺卡 / 缺勤</span
              ><strong>{{ absentAttendance }} 次</strong>
            </div>
          </div>
        </div>
      </section>
      <section class="panel todo-panel">
        <div class="panel-heading">
          <div>
            <h2>待处理事项</h2>
            <span>需要你关注的工作</span>
          </div>
          <el-button text type="primary">全部查看</el-button>
        </div>
        <div class="todo-list">
          <div v-for="todo in todos" :key="todo.title" class="todo-item">
            <div class="todo-marker" :class="todo.tone"></div>
            <div class="todo-content">
              <strong>{{ todo.title }}</strong
              ><span>{{ todo.detail }}</span>
            </div>
            <el-icon class="todo-arrow"><ArrowRight /></el-icon>
          </div>
        </div>
      </section>
    </div>
    <section class="panel activity-panel">
      <div class="panel-heading">
        <div>
          <h2>最近动态</h2>
          <span>系统内最新操作记录</span>
        </div>
        <el-button text type="primary" @click="checkHealth">刷新动态</el-button>
      </div>
      <el-table :data="activities" style="width: 100%" :show-header="true"
        ><el-table-column prop="action" label="操作" min-width="220" /><el-table-column
          prop="actor"
          label="操作人"
          width="150"
        /><el-table-column prop="time" label="时间" width="180" /><el-table-column
          label="状态"
          width="120"
          ><template #default="{ row }"
            ><el-tag :type="row.type" effect="light" size="small">{{
              row.status
            }}</el-tag></template
          ></el-table-column
        ></el-table
      >
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ArrowRight,
  CircleCheck,
  Clock,
  DocumentChecked,
  Refresh,
  User,
} from '@element-plus/icons-vue'
import { getHealth } from '../api/http'
import { attendanceApi, employeeApi, leaveApi, messageApi, salaryApi } from '../api'
import { formatDateTime } from '../utils/datetime'

const loading = ref(false)
const healthError = ref(false)
const currentMonth = ref(new Date().toISOString().slice(0, 7))
const attendanceRate = ref('0.0')
const normalAttendance = ref(0)
const attendanceExceptions = ref(0)
const absentAttendance = ref(0)
const activities = ref([])
const monthLabel = computed(
  () => `${currentMonth.value.slice(0, 4)} 年 ${Number(currentMonth.value.slice(5, 7))} 月`,
)
const stats = reactive([
  {
    label: '在职员工',
    value: '0',
    trend: '来自员工档案',
    trendClass: 'positive',
    tone: 'blue',
    icon: User,
  },
  {
    label: '本月出勤',
    value: '0',
    trend: '来自考勤汇总',
    trendClass: 'positive',
    tone: 'green',
    icon: CircleCheck,
  },
  {
    label: '待审批请假',
    value: '0',
    trend: '需要及时处理',
    trendClass: 'warning',
    tone: 'amber',
    icon: DocumentChecked,
  },
  {
    label: '未读消息',
    value: '0',
    trend: '来自消息中心',
    trendClass: 'positive',
    tone: 'red',
    icon: Clock,
  },
])
const todos = reactive([
  { title: '请假审批待处理', detail: '加载中', tone: 'amber' },
  { title: '月度薪酬待核对', detail: '加载中', tone: 'blue' },
  { title: '考勤异常提醒', detail: '加载中', tone: 'red' },
])

async function checkHealth() {
  loading.value = true
  healthError.value = false
  try {
    const month = currentMonth.value
    const [health, employees, attendance, leaves, messages, salary] = await Promise.all([
      getHealth(),
      employeeApi.list({ status: 'ACTIVE', page: 1, page_size: 1 }),
      attendanceApi.summary({ month }),
      leaveApi.pending(),
      messageApi.list({ unread_only: true }),
      salaryApi.records({ month }),
    ])
    if (health.status !== 'healthy') throw new Error('health check failed')
    stats[0].value = String(employees.data?.total || 0)
    const attendanceRows = attendance.data || []
    const attended = attendanceRows.reduce((total, item) => total + (item.attendance_days || 0), 0)
    const late = attendanceRows.reduce((total, item) => total + (item.late_count || 0), 0)
    const early = attendanceRows.reduce((total, item) => total + (item.early_leave_count || 0), 0)
    const absent = attendanceRows.reduce((total, item) => total + (item.absent_days || 0), 0)
    const leaveDays = attendanceRows.reduce((total, item) => total + (item.leave_days || 0), 0)
    const denominator = attended + absent + leaveDays
    attendanceRate.value = denominator ? ((attended / denominator) * 100).toFixed(1) : '0.0'
    normalAttendance.value = Math.max(0, attended - late - early)
    attendanceExceptions.value = late + early
    absentAttendance.value = absent
    stats[1].value = String(attended)
    stats[2].value = String((leaves.data || []).length)
    stats[3].value = String(messages.data?.unread_count || 0)
    todos[0].detail = `${stats[2].value} 条申请等待你的审批`
    const drafts = (salary.data || []).filter((item) => item.status === 'DRAFT').length
    todos[1].detail = `${drafts} 条工资条草稿待核对`
    todos[2].detail = `${attendanceExceptions.value + absentAttendance.value} 条考勤异常需要关注`
    activities.value = (messages.data?.items || []).slice(0, 5).map((item) => ({
      action: item.title,
      actor: '系统消息',
      time: formatDateTime(item.created_at),
      status: item.read_at ? '已读' : '未读',
      type: item.read_at ? 'info' : 'warning',
    }))
  } catch {
    healthError.value = true
  } finally {
    loading.value = false
  }
}
onMounted(checkHealth)
</script>
