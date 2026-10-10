<template>
  <div>
    <PageHeader title="员工工作台" description="查看今日状态，处理个人事务"
      ><el-button type="primary" :loading="working" @click="togglePunch">{{
        punchedIn ? '下班打卡' : '上班打卡'
      }}</el-button></PageHeader
    >
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-icon blue">👤</div>
        <div>
          <span class="stat-label">员工</span><strong>{{ profile?.name || '加载中' }}</strong
          ><small>{{ profile?.employee_no || '' }}</small>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon green">✓</div>
        <div>
          <span class="stat-label">本月出勤</span><strong>{{ attendanceDays }}</strong
          ><small>天</small>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon amber">!</div>
        <div>
          <span class="stat-label">年假余额</span><strong>{{ annualBalance }}</strong
          ><small>天</small>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon red">●</div>
        <div>
          <span class="stat-label">未读消息</span><strong>{{ unread }}</strong
          ><small>条</small>
        </div>
      </div>
    </div>
    <section class="panel">
      <h2>今日打卡</h2>
      <p v-if="punchMessage" class="page-subtitle">{{ punchMessage }}</p>
      <el-empty v-else description="暂未打卡" />
    </section>
  </div>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'
import { attendanceApi, messageApi, selfApi } from '../../api'
import { formatDateTime } from '../../utils/datetime'
const profile = ref(null),
  attendanceDays = ref(0),
  annualBalance = ref('0'),
  unread = ref(0),
  punchedIn = ref(false),
  working = ref(false),
  punchMessage = ref('')
async function load() {
  const month = new Date().toISOString().slice(0, 7)
  const [p, a, b, m] = await Promise.all([
    selfApi.profile(),
    selfApi.attendance({ month }),
    selfApi.leaveBalance({ year: new Date().getFullYear() }),
    messageApi.list({ unread_only: true }),
  ])
  profile.value = p.data
  attendanceDays.value = a.data.length
  annualBalance.value = b.data.find((x) => x.code === 'ANNUAL')?.remaining_days || '0'
  unread.value = m.data.unread_count || 0
  const today = new Date().toISOString().slice(0, 10)
  const row = a.data.find((x) => x.work_date === today)
  punchedIn.value = Boolean(row?.check_in_time && !row?.check_out_time)
  punchMessage.value = row
    ? `今日状态：${row.status}，上班 ${formatDateTime(row.check_in_time)}，下班 ${formatDateTime(row.check_out_time)}`
    : ''
}
async function togglePunch() {
  working.value = true
  try {
    const r = punchedIn.value ? await selfApi.checkOut() : await selfApi.checkIn()
    punchMessage.value = `${r.message || '打卡成功'}：上班 ${formatDateTime(r.data.check_in_time)}，下班 ${formatDateTime(r.data.check_out_time)}`
    punchedIn.value = !punchedIn.value
    ElMessage.success(r.message || '打卡成功')
  } catch (e) {
    ElMessage.error(e.businessMessage)
  } finally {
    working.value = false
  }
}
onMounted(() => load().catch((e) => ElMessage.error(e.businessMessage)))
</script>
