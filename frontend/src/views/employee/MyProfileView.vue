<template>
  <div>
    <PageHeader title="我的档案" description="以下信息由 HR 管理员维护，只读展示" />
    <section class="panel profile-grid">
      <div>
        <span>工号</span><strong>{{ profile.employee_no }}</strong>
      </div>
      <div>
        <span>姓名</span><strong>{{ profile.name }}</strong>
      </div>
      <div>
        <span>手机号</span><strong>{{ profile.phone }}</strong>
      </div>
      <div>
        <span>邮箱</span><strong>{{ profile.email || '-' }}</strong>
      </div>
      <div>
        <span>部门 ID</span><strong>{{ profile.department_id }}</strong>
      </div>
      <div>
        <span>岗位 ID</span><strong>{{ profile.position_id }}</strong>
      </div>
      <div>
        <span>入职日期</span><strong>{{ profile.hire_date }}</strong>
      </div>
      <div>
        <span>状态</span><strong>{{ profile.status }}</strong>
      </div>
    </section>
  </div>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'
import { selfApi } from '../../api'
const profile = ref({})
onMounted(async () => {
  try {
    profile.value = (await selfApi.profile()).data
  } catch (e) {
    ElMessage.error(e.businessMessage)
  }
})
</script>
