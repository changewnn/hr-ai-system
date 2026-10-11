import http from './http'

export const authApi = {
  login: (data) => http.post('/auth/login', data),
  me: () => http.get('/auth/me'),
  logout: () => http.post('/auth/logout'),
  changePassword: (data) => http.post('/auth/change-password', data),
}
export const accountApi = {
  list: () => http.get('/auth/accounts'),
  create: (data) => http.post('/auth/accounts', data),
  updateStatus: (id, enabled) => http.patch(`/auth/accounts/${id}/status`, { enabled }),
}
export const departmentApi = {
  list: () => http.get('/departments'),
  create: (data) => http.post('/departments', data),
  update: (id, data) => http.put(`/departments/${id}`, data),
  remove: (id) => http.delete(`/departments/${id}`),
}
export const positionApi = {
  list: () => http.get('/positions'),
  create: (data) => http.post('/positions', data),
  update: (id, data) => http.put(`/positions/${id}`, data),
  remove: (id) => http.delete(`/positions/${id}`),
}
export const employeeApi = {
  list: (params) => http.get('/employees', { params }),
  detail: (id) => http.get(`/employees/${id}`),
  create: (data) => http.post('/employees', data),
  update: (id, data) => http.put(`/employees/${id}`, data),
  resign: (id) => http.post(`/employees/${id}/resign`),
  export: () => http.get('/employees/export', { responseType: 'blob' }),
}
export const selfApi = {
  profile: () => http.get('/employees/me'),
  attendance: (params) => http.get('/attendance/mine', { params }),
  checkIn: () => http.post('/attendance/check-in'),
  checkOut: () => http.post('/attendance/check-out'),
  leaveTypes: () => http.get('/leaves/types'),
  leaveBalance: (params) => http.get('/leaves/my-balance', { params }),
  myLeaves: () => http.get('/leaves/my'),
  submitLeave: (data) => http.post('/leaves', data),
  cancelLeave: (id) => http.post(`/leaves/${id}/cancel`),
  salary: (params) => http.get('/salary/mine', { params }),
}
export const attendanceApi = {
  rule: () => http.get('/attendance/rule'),
  updateRule: (data) => http.put('/attendance/rule', data),
  records: (params) => http.get('/attendance/records', { params }),
  summary: (params) => http.get('/attendance/summary', { params }),
  adjust: (id, data) => http.patch(`/attendance/records/${id}/adjust`, data),
}
export const leaveApi = {
  pending: () => http.get('/leaves/pending'),
  review: (params) => http.get('/leaves/review', { params }),
  detail: (id) => http.get(`/leaves/${id}`),
  approve: (id, data) => http.post(`/leaves/${id}/approve`, data),
  types: () => http.get('/leaves/types'),
  createType: (data) => http.post('/leaves/types', data),
  updateType: (id, data) => http.put(`/leaves/types/${id}`, data),
  setBalance: (data) => http.put('/leaves/balances', data),
}
export const salaryApi = {
  configs: (params) => http.get('/salary/config', { params }),
  saveConfig: (data) => http.put('/salary/config', data),
  calculate: (data) => http.post('/salary/calculate', data),
  publish: (data) => http.post('/salary/publish', data),
  records: (params) => http.get('/salary/records', { params }),
  adjustment: (data) => http.post('/salary/adjustments', data),
}
export const messageApi = {
  list: (params) => http.get('/messages', { params }),
  read: (id) => http.patch(`/messages/${id}/read`),
  readAll: () => http.post('/messages/read-all'),
}
export const knowledgeApi = {
  list: (params) => http.get('/admin/knowledge', { params }),
  detail: (id) => http.get(`/admin/knowledge/${id}`),
  create: (data) => http.post('/admin/knowledge', data),
  uploadVersion: (id, data) => http.post(`/admin/knowledge/${id}/versions`, data),
  publish: (id) => http.post(`/admin/knowledge/versions/${id}/publish`),
  archive: (id) => http.post(`/admin/knowledge/versions/${id}/archive`),
  retry: (id) => http.post(`/admin/knowledge/versions/${id}/retry`),
  search: (data) => http.post('/admin/knowledge/search', data),
}
export const agentApi = {
  conversations: () => http.get('/agent/conversations'),
  createConversation: (data = {}) => http.post('/agent/conversations', data),
  conversation: (id) => http.get(`/agent/conversations/${id}`),
  rename: (id, data) => http.patch(`/agent/conversations/${id}`, data),
  message: (id, data) => http.post(`/agent/conversations/${id}/messages`, data),
  streamUrl: (id) => `${http.defaults.baseURL}/agent/conversations/${id}/messages/stream`,
  confirmLeave: (id, data) => http.post(`/agent/conversations/${id}/confirm-leave`, data),
}
