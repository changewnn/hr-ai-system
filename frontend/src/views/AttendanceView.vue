<template>
  <div>
    <PageHeader title="考勤管理" description="配置考勤规则，查询并修正异常记录"
      ><el-date-picker
        v-model="month"
        type="month"
        value-format="YYYY-MM"
        @change="loadSummary" /></PageHeader
    ><el-tabs v-model="tab"
      ><el-tab-pane label="月度汇总" name="summary"
        ><section class="panel">
          <el-table v-loading="loading" :data="summary"
            ><el-table-column prop="employee_id" label="员工 ID" /><el-table-column
              prop="attendance_days"
              label="出勤天数"
            /><el-table-column prop="late_count" label="迟到次数" /><el-table-column
              prop="early_leave_count"
              label="早退次数"
            /><el-table-column prop="leave_days" label="请假天数" /><el-table-column
              prop="absent_days"
              label="缺勤天数"
            /><el-table-column label="操作"
              ><template #default="{ row }"
                ><el-button link type="primary" @click="viewRecords(row.employee_id)"
                  >查看明细</el-button
                ></template
              ></el-table-column
            ></el-table
          >
        </section></el-tab-pane
      ><el-tab-pane label="考勤规则" name="rule"
        ><section class="panel form-panel">
          <el-form :model="rule" label-width="150px"
            ><el-form-item label="标准上下班"
              ><el-time-picker
                v-model="times"
                is-range
                value-format="HH:mm:ss"
                range-separator="至" /></el-form-item
            ><el-form-item label="迟到阈值（分钟）"
              ><el-input-number v-model="rule.late_threshold" :min="0" /></el-form-item
            ><el-form-item label="早退阈值（分钟）"
              ><el-input-number v-model="rule.early_leave_threshold" :min="0" /></el-form-item
            ><el-form-item label="工作日"
              ><el-checkbox-group v-model="rule.work_days"
                ><el-checkbox v-for="d in weekdays" :key="d.value" :value="d.value">{{
                  d.label
                }}</el-checkbox></el-checkbox-group
              ></el-form-item
            ><el-form-item label="单次扣款"
              ><el-input-number
                v-model="rule.single_deduct"
                :min="0"
                :precision="2" /></el-form-item
            ><el-form-item
              ><el-button type="primary" :loading="saving" @click="saveRule"
                >保存规则</el-button
              ></el-form-item
            ></el-form
          >
        </section></el-tab-pane
      ></el-tabs
    ><el-dialog v-model="recordsVisible" title="考勤明细" width="850"
      ><el-table :data="records"
        ><el-table-column prop="work_date" label="日期" /><el-table-column label="上班卡"
          ><template #default="{ row }">{{
            formatDateTime(row.check_in_time)
          }}</template></el-table-column
        ><el-table-column label="下班卡"
          ><template #default="{ row }">{{
            formatDateTime(row.check_out_time)
          }}</template></el-table-column
        ><el-table-column prop="status" label="状态" /><el-table-column
          prop="adjust_note"
          label="调整说明"
        /><el-table-column label="操作"
          ><template #default="{ row }"
            ><el-button link type="primary" @click="openAdjust(row)">调整</el-button></template
          ></el-table-column
        ></el-table
      ></el-dialog
    ><el-dialog v-model="adjustVisible" title="调整考勤" width="420"
      ><el-form label-position="top"
        ><el-form-item label="状态"
          ><el-select v-model="adjustForm.status"
            ><el-option
              v-for="s in statuses"
              :key="s"
              :value="s"
              :label="s" /></el-select></el-form-item
        ><el-form-item label="调整说明"
          ><el-input v-model="adjustForm.adjust_note" type="textarea" /></el-form-item></el-form
      ><template #footer
        ><el-button @click="adjustVisible = false">取消</el-button
        ><el-button type="primary" @click="saveAdjust">保存</el-button></template
      ></el-dialog
    >
  </div>
</template>
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import { attendanceApi } from '../api'
import { formatDateTime } from '../utils/datetime'
const tab = ref('summary'),
  month = ref(new Date().toISOString().slice(0, 7)),
  summary = ref([]),
  records = ref([]),
  loading = ref(false),
  saving = ref(false),
  recordsVisible = ref(false),
  adjustVisible = ref(false),
  employeeId = ref(null),
  currentRecord = ref(null)
const weekdays = [
    { label: '周一', value: 1 },
    { label: '周二', value: 2 },
    { label: '周三', value: 3 },
    { label: '周四', value: 4 },
    { label: '周五', value: 5 },
    { label: '周六', value: 6 },
    { label: '周日', value: 7 },
  ],
  statuses = ['NORMAL', 'LATE', 'EARLY_LEAVE', 'MISSING', 'LEAVE']
const rule = reactive({
  work_start_time: '09:00:00',
  work_end_time: '18:00:00',
  late_threshold: 5,
  early_leave_threshold: 5,
  work_days: [1, 2, 3, 4, 5],
  single_deduct: 20,
})
const times = computed({
  get: () => [rule.work_start_time, rule.work_end_time],
  set: (v) => {
    if (v) {
      rule.work_start_time = v[0]
      rule.work_end_time = v[1]
    }
  },
})
const adjustForm = reactive({ status: 'NORMAL', adjust_note: '' })
async function loadRule() {
  Object.assign(rule, (await attendanceApi.rule()).data)
  rule.single_deduct = Number(rule.single_deduct)
}
async function loadSummary() {
  loading.value = true
  try {
    summary.value = (await attendanceApi.summary({ month: month.value })).data || []
  } catch (e) {
    ElMessage.error(e.businessMessage)
  } finally {
    loading.value = false
  }
}
async function saveRule() {
  saving.value = true
  try {
    await attendanceApi.updateRule({ ...rule, single_deduct: String(rule.single_deduct) })
    ElMessage.success('规则已保存')
  } catch (e) {
    ElMessage.error(e.businessMessage)
  } finally {
    saving.value = false
  }
}
async function viewRecords(id) {
  employeeId.value = id
  records.value = (await attendanceApi.records({ month: month.value, employee_id: id })).data || []
  recordsVisible.value = true
}
function openAdjust(row) {
  currentRecord.value = row
  Object.assign(adjustForm, { status: row.status, adjust_note: row.adjust_note || '' })
  adjustVisible.value = true
}
async function saveAdjust() {
  if (!adjustForm.adjust_note) return ElMessage.warning('请输入调整说明')
  try {
    await attendanceApi.adjust(currentRecord.value.id, adjustForm)
    ElMessage.success('调整成功')
    adjustVisible.value = false
    await viewRecords(employeeId.value)
    await loadSummary()
  } catch (e) {
    ElMessage.error(e.businessMessage)
  }
}
onMounted(() =>
  Promise.all([loadRule(), loadSummary()]).catch((e) => ElMessage.error(e.businessMessage)),
)
</script>
