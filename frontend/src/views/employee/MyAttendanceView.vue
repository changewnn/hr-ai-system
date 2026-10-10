<template>
  <div>
    <PageHeader title="我的考勤" description="按月查看本人考勤记录"
      ><el-date-picker v-model="month" type="month" value-format="YYYY-MM" @change="load"
    /></PageHeader>
    <section class="panel">
      <el-table :data="rows" v-loading="loading"
        ><el-table-column prop="work_date" label="日期" /><el-table-column label="上班时间"
          ><template #default="{ row }">{{
            formatDateTime(row.check_in_time)
          }}</template></el-table-column
        ><el-table-column label="下班时间"
          ><template #default="{ row }">{{
            formatDateTime(row.check_out_time)
          }}</template></el-table-column
        ><el-table-column prop="status" label="状态" /></el-table
      ><el-empty v-if="!loading && !rows.length" description="暂无考勤记录" />
    </section>
  </div>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'
import { selfApi } from '../../api'
import { formatDateTime } from '../../utils/datetime'
const month = ref(new Date().toISOString().slice(0, 7)),
  rows = ref([]),
  loading = ref(false)
async function load() {
  loading.value = true
  try {
    rows.value = (await selfApi.attendance({ month: month.value })).data || []
  } catch (e) {
    ElMessage.error(e.businessMessage)
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
