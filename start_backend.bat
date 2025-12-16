@echo off
echo ====================================
echo Запуск Backend сервера
echo ====================================
cd backend

if not exist venv (
    echo Создание виртуального окружения...
    python -m venv venv
)

echo Активация виртуального окружения...
call venv\Scripts\activate.bat

echo Обновление pip...
python -m pip install --upgrade pip setuptools wheel

echo Установка зависимостей...
echo Если возникнут ошибки с компиляцией, используйте backend\install_simple.bat
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings python-multipart httpx python-jose cryptography bcrypt

echo Запуск сервера на http://localhost:8000
python main.py

pause

