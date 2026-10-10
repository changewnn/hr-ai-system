import axios from 'axios'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 8000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('hr_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('hr_access_token')
      localStorage.removeItem('hr_user')
      if (window.location.pathname !== '/login') window.location.assign('/login')
    }
    error.businessMessage = error.response?.data?.message || error.message || '请求失败'
    return Promise.reject(error)
  },
)

export const getHealth = () => http.get('/health')
export default http
