<template>
  <div>
    <PageHeader title="智能助手" description="查询个人事务前，涉及提交或变更的操作需要二次确认" />
    <section class="panel agent-panel">
      <el-input
        v-model="question"
        placeholder="例如：我还有多少年假？"
        @keyup.enter="ask"
      /><el-button type="primary" @click="ask">发送</el-button>
      <div v-if="answer" class="agent-answer">
        <strong>助手</strong>
        <p>{{ answer }}</p>
        <el-alert
          v-if="needsConfirm"
          title="该操作会提交业务申请，请确认后再继续"
          type="warning"
          show-icon
        /><el-button v-if="needsConfirm" type="primary" @click="confirmAction">确认提交</el-button>
      </div>
    </section>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'
const question = ref(''),
  answer = ref(''),
  needsConfirm = ref(false)
function ask() {
  if (!question.value.trim()) return
  needsConfirm.value = /请假|申请|提交/.test(question.value)
  answer.value = needsConfirm.value
    ? '我可以帮你准备申请，请确认后提交。'
    : '我会基于你的员工档案和已发布数据提供查询结果。'
}
function confirmAction() {
  needsConfirm.value = false
  ElMessage.success('已确认，后续业务申请请在对应页面完成提交')
}
</script>
