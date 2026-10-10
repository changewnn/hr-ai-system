<template>
  <div>
    <PageHeader title="我的工资条" description="查看已发布的个人工资条"
      ><el-date-picker v-model="month" type="month" value-format="YYYY-MM" @change="load"
    /></PageHeader>
    <section class="panel">
      <el-table :data="rows"
        ><el-table-column prop="month" label="月份" /><el-table-column
          prop="gross_salary"
          label="应发工资" /><el-table-column prop="tax" label="个人所得税" /><el-table-column
          prop="net_salary"
          label="实发工资" /><el-table-column prop="published_at" label="发布时间" /></el-table
      ><el-empty v-if="!rows.length" description="暂无已发布工资条" />
    </section>
  </div>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'
import { selfApi } from '../../api'
const month = ref(''),
  rows = ref([])
async function load() {
  try {
    const r = await selfApi.salary(month.value ? { month: month.value } : {})
    rows.value = r.data || []
  } catch (e) {
    ElMessage.error(e.businessMessage)
  }
}
onMounted(load)
</script>
