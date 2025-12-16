import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Добавляем токен к каждому запросу
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Обрабатываем ошибки авторизации
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Логируем ошибки для отладки
    if (error.response) {
      console.error('API Error:', error.response.status, error.response.data)
    } else if (error.request) {
      console.error('Network Error:', 'Не удалось подключиться к серверу')
    } else {
      console.error('Error:', error.message)
    }
    
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authService = {
  register: async (userData) => {
    const response = await api.post('/auth/register', userData)
    return response.data
  },
  
  login: async (credentials) => {
    const response = await api.post('/auth/login', credentials)
    return response.data
  },
  
  getCurrentUser: async () => {
    const response = await api.get('/auth/me')
    return response.data
  },
}

export const documentService = {
  upload: async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
  
  getDocuments: async () => {
    const response = await api.get('/documents')
    return response.data
  },
}

export const chatService = {
  createChat: async (title) => {
    const response = await api.post('/chats', { title })
    return response.data
  },
  
  getChats: async () => {
    const response = await api.get('/chats')
    return response.data
  },
  
  getMessages: async (chatId) => {
    const response = await api.get(`/chats/${chatId}/messages`)
    return response.data
  },
  
  sendMessage: async (chatId, content) => {
    const response = await api.post(`/chats/${chatId}/messages`, { content })
    return response.data
  },
  
  deleteChat: async (chatId) => {
    const response = await api.delete(`/chats/${chatId}`)
    return response.data
  },
}

export default api

