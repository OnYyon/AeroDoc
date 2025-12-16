@echo off
echo ====================================
echo Установка зависимостей Backend
echo ====================================

echo Обновление pip...
python -m pip install --upgrade pip

echo Установка зависимостей без компиляции (используя предкомпилированные пакеты)...
pip install --only-binary :all: fastapi uvicorn sqlalchemy pydantic pydantic-settings python-multipart httpx

echo Установка python-jose и cryptography...
pip install python-jose[cryptography]

echo Установка bcrypt (может потребоваться время)...
pip install bcrypt

echo.
echo ====================================
echo Проверка установленных пакетов...
echo ====================================
pip list | findstr "fastapi uvicorn sqlalchemy pydantic bcrypt"

echo.
echo ====================================
echo Готово! Теперь можно запустить: python main.py
echo ====================================
pause

