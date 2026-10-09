import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const unreadMessages = ref(3)
  const displayName = ref('HR 管理员')
  const roleLabel = ref('ADMIN')

  const sidebarWidth = computed(() => (sidebarCollapsed.value ? '72px' : '232px'))
  const toggleSidebar = () => { sidebarCollapsed.value = !sidebarCollapsed.value }

  return { sidebarCollapsed, unreadMessages, displayName, roleLabel, sidebarWidth, toggleSidebar }
})
