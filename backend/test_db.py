"""
Скрипт для проверки подключения к базе данных
"""
from database import engine, Base
from models import User, Chat, Message, Document, DocumentAccess

try:
    # Пытаемся создать таблицы
    Base.metadata.create_all(bind=engine)
    print("✓ База данных успешно создана/проверена")
    print("✓ Таблицы созданы успешно")
    
    # Проверяем подключение
    with engine.connect() as conn:
        print("✓ Подключение к базе данных работает")
    
except Exception as e:
    print(f"✗ Ошибка: {e}")
    import traceback
    traceback.print_exc()

