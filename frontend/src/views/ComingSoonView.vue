<template><div class="empty-page"><div class="empty-mark"><el-icon size="28"><Tools /></el-icon></div><p class="eyebrow">MODULE</p><h1>{{ $route.meta.title }}</h1><p>该模块将在后续开发阶段接入业务 API。</p><el-button type="primary" @click="$router.push('/dashboard')">返回工作台</el-button></div></template>
<script setup>import { Tools } from '@element-plus/icons-vue'</script>
