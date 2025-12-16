"""
Скрипт для принудительной инициализации базы данных
"""
from database import engine, Base
from models import User, Chat, Message, Document, DocumentAccess

def init_db():
    """Создает все таблицы в базе данных"""
    try:
        print("Создание таблиц в базе данных...")
        Base.metadata.create_all(bind=engine)
        print("✓ Таблицы успешно созданы!")
        print("✓ База данных готова к использованию")
        return True
    except Exception as e:
        print(f"✗ Ошибка при создании таблиц: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    init_db()

