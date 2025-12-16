import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authService } from '../services/api'
import './Auth.css'

const ROLES = [
  { value: 'engineer', label: 'Инженер' },
  { value: 'technician', label: 'Техник' },
  { value: 'quality_control', label: 'Контроль качества' },
  { value: 'project_manager', label: 'Менеджер проектов' },
  { value: 'maintenance', label: 'Обслуживающий персонал' },
  { value: 'admin', label: 'Администратор' },
]

function Register({ onLogin }) {
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    role: 'technician'
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await authService.register(formData)
      // После регистрации автоматически входим
      const loginResponse = await authService.login({
        email: formData.email,
        password: formData.password
      })
      localStorage.setItem('token', loginResponse.access_token)
      localStorage.setItem('user', JSON.stringify(loginResponse.user))
      onLogin()
      navigate('/')
    } catch (err) {
      console.error('Ошибка регистрации:', err)
      const errorMessage = err.response?.data?.detail || err.message || 'Ошибка регистрации'
      setError(errorMessage)
      // Если это ошибка сети, показываем более понятное сообщение
      if (!err.response) {
        setError('Не удалось подключиться к серверу. Убедитесь, что backend запущен на http://localhost:8000')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>AeroDoc Assistant</h1>
        <h2>Регистрация</h2>
        {error && <div className="error-message">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              placeholder="your.email@example.com"
            />
          </div>
          <div className="form-group">
            <label>Имя пользователя</label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              required
              placeholder="Ваше имя"
            />
          </div>
          <div className="form-group">
            <label>Пароль</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              placeholder="Минимум 6 символов"
              minLength={6}
            />
          </div>
          <div className="form-group">
            <label>Роль</label>
            <select
              name="role"
              value={formData.role}
              onChange={handleChange}
              required
            >
              {ROLES.map(role => (
                <option key={role.value} value={role.value}>
                  {role.label}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" disabled={loading}>
            {loading ? 'Регистрация...' : 'Зарегистрироваться'}
          </button>
        </form>
        <p className="auth-link">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </div>
    </div>
  )
}

export default Register

