@echo off
echo ====================================
echo Простая установка зависимостей
echo ====================================

echo Обновление pip...
python -m pip install --upgrade pip setuptools wheel

echo Установка зависимостей...
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings python-multipart httpx python-jose "cryptography>=3.4.8" bcrypt

echo.
echo ====================================
if %ERRORLEVEL% EQU 0 (
    echo Установка завершена успешно!
) else (
    echo Произошла ошибка при установке.
    echo Попробуйте установить зависимости вручную:
    echo pip install -r requirements.txt
)
echo ====================================
pause

