@echo off
echo ====================================
echo Запуск Frontend сервера
echo ====================================
cd frontend

if not exist node_modules (
    echo Установка зависимостей...
    call npm install
)

echo Запуск dev-сервера на http://localhost:3000
call npm run dev

pause

