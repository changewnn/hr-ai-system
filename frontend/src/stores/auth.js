import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { authApi } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('hr_access_token') || '')
  const user = ref(JSON.parse(localStorage.getItem('hr_user') || 'null'))
  const isAuthenticated = computed(() => Boolean(token.value))
  const isAdmin = computed(() => user.value?.role === 'ADMIN')
  const canUseEmployeePortal = computed(() => Boolean(user.value?.employee_id))
  function persist() { token.value ? localStorage.setItem('hr_access_token', token.value) : localStorage.removeItem('hr_access_token'); user.value ? localStorage.setItem('hr_user', JSON.stringify(user.value)) : localStorage.removeItem('hr_user') }
  async function login(identifier, password) { const response = await authApi.login({ identifier, password }); token.value = response.data.access_token; user.value = response.data.user; persist(); return user.value }
  async function loadMe() { if (!token.value) return null; const response = await authApi.me(); user.value = response.data; persist(); return user.value }
  async function logout() { try { if (token.value) await authApi.logout() } finally { token.value = ''; user.value = null; persist() } }
  async function changePassword(oldPassword, newPassword) { await authApi.changePassword({ old_password: oldPassword, new_password: newPassword }); user.value = { ...user.value, must_change_password: false }; persist() }
  return { token, user, isAuthenticated, isAdmin, canUseEmployeePortal, login, loadMe, logout, changePassword }
})
