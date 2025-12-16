# Быстрый старт AeroDoc Assistant

## Шаг 1: Установка зависимостей Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

## Шаг 2: Запуск Backend

```bash
python main.py
```

Backend будет доступен на `http://localhost:8000`

## Шаг 3: Установка зависимостей Frontend

Откройте новый терминал:

```bash
cd frontend
npm install
```

## Шаг 4: Запуск Frontend

```bash
npm run dev
```

Frontend будет доступен на `http://localhost:3000`

## Шаг 5: Использование

1. Откройте браузер и перейдите на `http://localhost:3000`
2. Зарегистрируйтесь, выбрав роль
3. Загрузите документы через кнопку "Загрузить документ"
4. Создайте новый чат и начните общение

## Примечание о ML-сервисе

По умолчанию система ожидает ML-сервис на `http://localhost:8001/api/ml/process`.

Если ML-сервис не запущен, система будет показывать сообщение об ошибке при отправке сообщений.

Для изменения URL ML-сервиса создайте файл `.env` в директории `backend`:

```env
ML_SERVICE_URL=http://your-ml-service-url/api/ml/process
```

## Формат запроса к ML-сервису

```json
{
  "question": "текст вопроса пользователя",
  "document_paths": ["полный/путь/к/документу1.pdf", "полный/путь/к/документу2.pdf"],
  "user_role": "engineer"
}
```

## Формат ответа от ML-сервиса

```json
{
  "answer": "ответ от ML-сервиса"
}
```

