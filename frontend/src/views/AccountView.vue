<template>
  <div>
    <PageHeader title="账号管理" description="创建员工登录账号、绑定员工档案并管理账号状态">
      <el-button type="primary" :icon="Plus" @click="openCreate">创建账号</el-button>
    </PageHeader>
    <section class="panel">
      <el-table v-loading="loading" :data="accounts">
        <el-table-column prop="username" label="登录账号" min-width="180" />
        <el-table-column prop="role" label="角色" width="120" />
        <el-table-column prop="employee_id" label="绑定员工 ID" width="130"
          ><template #default="{ row }">{{
            row.employee_id || '未绑定'
          }}</template></el-table-column
        >
        <el-table-column prop="status" label="状态" width="110"
          ><template #default="{ row }"
            ><el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'">{{
              row.status === 'ACTIVE' ? '启用' : '停用'
            }}</el-tag></template
          ></el-table-column
        >
        <el-table-column prop="must_change_password" label="首次改密" width="110"
          ><template #default="{ row }">{{
            row.must_change_password ? '待修改' : '已完成'
          }}</template></el-table-column
        >
        <el-table-column label="操作" width="120"
          ><template #default="{ row }"
            ><el-button
              link
              :type="row.status === 'ACTIVE' ? 'danger' : 'success'"
              @click="toggle(row)"
              >{{ row.status === 'ACTIVE' ? '停用' : '启用' }}</el-button
            ></template
          ></el-table-column
        >
      </el-table>
      <el-empty v-if="!loading && !accounts.length" description="暂无账号" />
    </section>
    <el-dialog v-model="visible" title="创建登录账号" width="520">
      <el-alert
        title="员工首次登录后必须修改临时密码。账号名默认使用手机号，员工也可以使用手机号登录。"
        type="info"
        :closable="false"
        show-icon
        class="account-tip"
      />
      <el-form label-position="top">
        <el-form-item label="绑定员工" required
          ><el-select
            v-model="form.employee_id"
            filterable
            placeholder="选择员工"
            @change="employeeChanged"
            ><el-option
              v-for="employee in employees"
              :key="employee.id"
              :label="`${employee.name} / ${employee.employee_no} / ${employee.phone}`"
              :value="employee.id" /></el-select
        ></el-form-item>
        <el-form-item label="登录账号" required
          ><el-input v-model="form.username" placeholder="默认填员工手机号"
        /></el-form-item>
        <el-form-item label="角色" required
          ><el-select v-model="form.role"
            ><el-option label="普通员工" value="EMPLOYEE" /><el-option
              label="部门主管"
              value="MANAGER" /><el-option label="管理员" value="ADMIN" /></el-select
        ></el-form-item>
        <el-form-item label="临时密码" required
          ><el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="至少 8 位，包含字母和数字"
        /></el-form-item>
      </el-form>
      <template #footer
        ><el-button @click="visible = false">取消</el-button
        ><el-button type="primary" :loading="saving" @click="save">创建账号</el-button></template
      >
    </el-dialog>
  </div>
</template>
<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import { accountApi, employeeApi } from '../api'
const accounts = ref([])
const employees = ref([])
const loading = ref(false)
const saving = ref(false)
const visible = ref(false)
const form = reactive({ employee_id: null, username: '', role: 'EMPLOYEE', password: '' })
async function load() {
  loading.value = true
  try {
    const [a, e] = await Promise.all([
      accountApi.list(),
      employeeApi.list({ status: 'ACTIVE', page: 1, page_size: 100 }),
    ])
    accounts.value = a.data || []
    employees.value = e.data?.items || []
  } catch (error) {
    ElMessage.error(error.businessMessage)
  } finally {
    loading.value = false
  }
}
function openCreate() {
  Object.assign(form, { employee_id: null, username: '', role: 'EMPLOYEE', password: '' })
  visible.value = true
}
function employeeChanged(id) {
  const employee = employees.value.find((item) => item.id === id)
  if (employee && !form.username) form.username = employee.phone
}
async function save() {
  if (!form.employee_id || !form.username || !form.password)
    return ElMessage.warning('请完整填写账号信息')
  saving.value = true
  try {
    await accountApi.create(form)
    ElMessage.success('账号创建成功，员工可使用手机号登录')
    visible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error.businessMessage)
  } finally {
    saving.value = false
  }
}
async function toggle(row) {
  try {
    await ElMessageBox.confirm(
      `确认${row.status === 'ACTIVE' ? '停用' : '启用'}账号“${row.username}”？`,
      '账号状态',
      { type: 'warning' },
    )
    await accountApi.updateStatus(row.id, row.status !== 'ACTIVE')
    ElMessage.success('账号状态已更新')
    await load()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error.businessMessage)
  }
}
onMounted(load)
</script>
