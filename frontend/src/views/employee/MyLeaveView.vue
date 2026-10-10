<template>
  <div>
    <PageHeader title="我的请假" description="提交申请并跟踪审批进度"
      ><el-button type="primary" @click="visible = true">申请请假</el-button></PageHeader
    >
    <section class="panel leave-balance">
      <span v-for="b in balances" :key="b.leave_type_id"
        >{{ b.name }}余额：<strong>{{ b.remaining_days }}</strong> 天</span
      >
    </section>
    <section class="panel">
      <el-table :data="rows"
        ><el-table-column prop="request_no" label="申请单号" /><el-table-column
          prop="start_date"
          label="开始日期"
        /><el-table-column prop="end_date" label="结束日期" /><el-table-column
          prop="days"
          label="天数"
        /><el-table-column prop="status" label="状态" /><el-table-column label="操作"
          ><template #default="{ row }"
            ><el-button v-if="row.status === 'PENDING'" link type="danger" @click="cancel(row.id)"
              >撤销</el-button
            ></template
          ></el-table-column
        ></el-table
      >
    </section>
    <el-dialog v-model="visible" title="申请请假" width="520"
      ><el-form label-position="top"
        ><el-form-item label="请假类型"
          ><el-select v-model="form.leave_type_id"
            ><el-option
              v-for="t in types"
              :key="t.id"
              :label="t.name"
              :value="t.id" /></el-select></el-form-item
        ><el-form-item label="日期"
          ><el-date-picker
            v-model="dates"
            type="daterange"
            value-format="YYYY-MM-DD" /></el-form-item
        ><el-form-item label="事由"
          ><el-input v-model="form.reason" type="textarea" /></el-form-item></el-form
      ><template #footer
        ><el-button @click="visible = false">取消</el-button
        ><el-button type="primary" @click="submit">提交</el-button></template
      ></el-dialog
    >
  </div>
</template>
<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'
import { selfApi } from '../../api'
const rows = ref([]),
  types = ref([]),
  balances = ref([]),
  visible = ref(false),
  dates = ref([]),
  form = reactive({ leave_type_id: null, reason: '' })
async function load() {
  const [r, t, b] = await Promise.all([
    selfApi.myLeaves(),
    selfApi.leaveTypes(),
    selfApi.leaveBalance({ year: new Date().getFullYear() }),
  ])
  rows.value = r.data || []
  types.value = t.data || []
  balances.value = b.data || []
}
async function submit() {
  if (!form.leave_type_id || dates.value.length !== 2 || !form.reason)
    return ElMessage.warning('请完整填写申请')
  try {
    await selfApi.submitLeave({
      leave_type_id: form.leave_type_id,
      start_date: dates.value[0],
      end_date: dates.value[1],
      start_period: 'FULL_DAY',
      end_period: 'FULL_DAY',
      reason: form.reason,
    })
    ElMessage.success('申请已提交')
    visible.value = false
    Object.assign(form, { leave_type_id: null, reason: '' })
    dates.value = []
    await load()
  } catch (e) {
    ElMessage.error(e.businessMessage)
  }
}
async function cancel(id) {
  try {
    await ElMessageBox.confirm('确认撤销该申请？', '提示')
    await selfApi.cancelLeave(id)
    ElMessage.success('已撤销')
    await load()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.businessMessage)
  }
}
onMounted(() => load().catch((e) => ElMessage.error(e.businessMessage)))
</script>
