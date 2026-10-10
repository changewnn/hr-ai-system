<template><main class="auth-page"><section class="auth-panel"><div class="auth-brand"><div class="brand-mark">HR</div><div><strong>HR AI System</strong><span>人事管理平台</span></div></div><div class="auth-heading"><h1>登录</h1><p>使用工号、手机号或管理员账号进入系统</p></div><el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit"><el-form-item label="账号" prop="identifier"><el-input v-model="form.identifier" size="large" autocomplete="username" placeholder="请输入工号或手机号" /></el-form-item><el-form-item label="密码" prop="password"><el-input v-model="form.password" size="large" type="password" show-password autocomplete="current-password" placeholder="请输入密码" @keyup.enter="submit" /></el-form-item><el-button type="primary" size="large" class="auth-submit" :loading="loading" @click="submit">登录</el-button></el-form></section></main></template>
<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore(); const route = useRoute(); const router = useRouter(); const formRef = ref(); const loading = ref(false)
const form = reactive({ identifier: '', password: '' }); const rules = { identifier: [{ required: true, message: '请输入账号', trigger: 'blur' }], password: [{ required: true, message: '请输入密码', trigger: 'blur' }] }
async function submit() { if (!(await formRef.value.validate().catch(() => false))) return; loading.value = true; try { const user = await auth.login(form.identifier, form.password); ElMessage.success('登录成功'); await router.replace(user.must_change_password ? '/change-password' : (route.query.redirect || '/dashboard')) } catch (error) { ElMessage.error(error.businessMessage) } finally { loading.value = false } }
</script>
