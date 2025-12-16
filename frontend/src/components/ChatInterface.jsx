import React, { useState, useEffect, useRef } from 'react'
import { chatService, documentService } from '../services/api'
import { Upload, Send, Plus, Trash2, FileText, LogOut } from 'lucide-react'
import './ChatInterface.css'

function ChatInterface({ onLogout }) {
  const [chats, setChats] = useState([])
  const [currentChat, setCurrentChat] = useState(null)
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [user, setUser] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    const userData = localStorage.getItem('user')
    if (userData) {
      setUser(JSON.parse(userData))
    }
    loadChats()
  }, [])

  useEffect(() => {
    if (currentChat) {
      loadMessages(currentChat.id)
    }
  }, [currentChat])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadChats = async () => {
    try {
      const data = await chatService.getChats()
      setChats(data)
      if (data.length > 0 && !currentChat) {
        setCurrentChat(data[0])
      }
    } catch (error) {
      console.error('Ошибка загрузки чатов:', error)
    }
  }

  const loadMessages = async (chatId) => {
    try {
      const data = await chatService.getMessages(chatId)
      setMessages(data)
    } catch (error) {
      console.error('Ошибка загрузки сообщений:', error)
    }
  }

  const createNewChat = async () => {
    try {
      const newChat = await chatService.createChat('Новый чат')
      setChats([newChat, ...chats])
      setCurrentChat(newChat)
      setMessages([])
    } catch (error) {
      console.error('Ошибка создания чата:', error)
    }
  }

  const deleteChat = async (chatId, e) => {
    e.stopPropagation()
    try {
      await chatService.deleteChat(chatId)
      setChats(chats.filter(chat => chat.id !== chatId))
      if (currentChat?.id === chatId) {
        if (chats.length > 1) {
          const nextChat = chats.find(chat => chat.id !== chatId)
          setCurrentChat(nextChat || null)
        } else {
          setCurrentChat(null)
          setMessages([])
        }
      }
    } catch (error) {
      console.error('Ошибка удаления чата:', error)
    }
  }

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !currentChat || loading) return

    const userMessage = {
      id: Date.now(),
      content: inputMessage,
      role: 'user',
      created_at: new Date().toISOString()
    }

    setMessages([...messages, userMessage])
    setInputMessage('')
    setLoading(true)

    try {
      const response = await chatService.sendMessage(currentChat.id, inputMessage)
      setMessages(prev => [...prev, response])
      await loadChats() // Обновляем список чатов для обновления времени
    } catch (error) {
      console.error('Ошибка отправки сообщения:', error)
      const errorMessage = {
        id: Date.now(),
        content: 'Ошибка отправки сообщения. Попробуйте еще раз.',
        role: 'assistant',
        created_at: new Date().toISOString()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const uploadFile = async (file) => {
    if (!file) return
    setUploading(true)
    try {
      const response = await documentService.upload(file)
      alert(`Документ "${response.filename}" успешно загружен!\nПуть: ${response.file_path}`)
    } catch (error) {
      console.error('Ошибка загрузки файла:', error)
      alert('Ошибка загрузки файла: ' + (error.response?.data?.detail || error.message))
    } finally {
      setUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    await uploadFile(file)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = async (e) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (!file) return
    await uploadFile(file)
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now - date
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (days === 0) {
      return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
    } else if (days === 1) {
      return 'Вчера'
    } else if (days < 7) {
      return `${days} дн. назад`
    } else {
      return date.toLocaleDateString('ru-RU')
    }
  }

  return (
    <div className="chat-container">
      <div className="sidebar">
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={createNewChat}>
            <Plus size={20} />
            Новый чат
          </button>
          <button className="upload-btn" onClick={() => fileInputRef.current?.click()}>
            <Upload size={20} />
            Загрузить документ
          </button>
          <input
            ref={fileInputRef}
            type="file"
            style={{ display: 'none' }}
            onChange={handleFileUpload}
            accept=".pdf,.docx,.doc,.txt,.json,.xml"
            disabled={uploading}
          />
        </div>
        <div className="chats-list">
          {chats.map(chat => (
            <div
              key={chat.id}
              className={`chat-item ${currentChat?.id === chat.id ? 'active' : ''}`}
              onClick={() => setCurrentChat(chat)}
            >
              <FileText size={16} />
              <span className="chat-title">{chat.title}</span>
              <span className="chat-date">{formatDate(chat.updated_at)}</span>
              <button
                className="delete-chat-btn"
                onClick={(e) => deleteChat(chat.id, e)}
                title="Удалить чат"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
        <div className="sidebar-footer">
          <div className="user-info">
            <span>{user?.username}</span>
            <span className="user-role">{user?.role}</span>
          </div>
          <button className="logout-btn" onClick={onLogout}>
            <LogOut size={16} />
            Выйти
          </button>
        </div>
      </div>

      <div
        className="chat-main"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {currentChat ? (
          <>
            <div className="messages-container">
              {isDragging && (
                <div className="drop-overlay">
                  <div className="drop-box">
                    <Upload size={24} />
                    <p>Перетащите документ для загрузки</p>
                    <span className="drop-hint">Поддержка: pdf, docx, doc, txt, json, xml</span>
                  </div>
                </div>
              )}
              {messages.map(message => (
                <div
                  key={message.id}
                  className={`message ${message.role === 'user' ? 'user-message' : 'assistant-message'}`}
                >
                  <div className="message-content">
                    {message.content}
                  </div>
                  <div className="message-time">
                    {new Date(message.created_at).toLocaleTimeString('ru-RU', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="message assistant-message">
                  <div className="message-content">
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            <div className="input-container">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                placeholder="Введите сообщение..."
                disabled={loading}
              />
              <button onClick={handleSendMessage} disabled={loading || !inputMessage.trim()}>
                <Send size={20} />
              </button>
            </div>
          </>
        ) : (
          <div className="empty-chat">
            <h2>Выберите чат или создайте новый</h2>
            <p>Начните общение с AeroDoc Assistant</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatInterface

