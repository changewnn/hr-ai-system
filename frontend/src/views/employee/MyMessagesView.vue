<template>
  <div>
    <PageHeader title="我的消息" description="查看审批结果和系统通知"
      ><el-button @click="readAll">全部已读</el-button></PageHeader
    >
    <section class="panel">
      <el-table :data="rows"
        ><el-table-column prop="title" label="标题" /><el-table-column
          prop="content"
          label="内容"
        /><el-table-column prop="created_at" label="时间" /><el-table-column label="状态"
          ><template #default="{ row }"
            ><el-tag :type="row.read_at ? 'info' : 'warning'">{{
              row.read_at ? '已读' : '未读'
            }}</el-tag
            ><el-button v-if="!row.read_at" link @click="read(row.id)"
              >标记已读</el-button
            ></template
          ></el-table-column
        ></el-table
      >
    </section>
  </div>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'
import { messageApi } from '../../api'
const rows = ref([])
async function load() {
  rows.value = (await messageApi.list()).data?.items || []
}
async function read(id) {
  await messageApi.read(id)
  await load()
}
async function readAll() {
  await messageApi.readAll()
  ElMessage.success('已全部标记为已读')
  await load()
}
onMounted(() => load().catch((e) => ElMessage.error(e.businessMessage)))
</script>
