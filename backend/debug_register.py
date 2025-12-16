"""
Скрипт для отладки регистрации
"""
import sys
sys.path.insert(0, '.')

from database import engine, Base, SessionLocal
from models import User, UserRole
from sqlalchemy import text

print("=" * 50)
print("Отладка регистрации")
print("=" * 50)

# Проверка подключения к БД
print("\n1. Проверка подключения к базе данных...")
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✓ Подключение работает")
except Exception as e:
    print(f"✗ Ошибка подключения: {e}")
    sys.exit(1)

# Проверка существования таблиц
print("\n2. Проверка существования таблиц...")
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
        print(f"Найдено таблиц: {len(tables)}")
        for table in tables:
            print(f"  - {table}")
        
        if 'users' not in tables:
            print("\n⚠ Таблица 'users' не найдена. Создаю таблицы...")
            Base.metadata.create_all(bind=engine)
            print("✓ Таблицы созданы")
        else:
            print("✓ Таблица 'users' существует")
except Exception as e:
    print(f"✗ Ошибка: {e}")
    import traceback
    traceback.print_exc()

# Проверка модели User
print("\n3. Проверка модели User...")
try:
    db = SessionLocal()
    count = db.query(User).count()
    print(f"✓ Модель User работает. Пользователей в БД: {count}")
    db.close()
except Exception as e:
    print(f"✗ Ошибка модели User: {e}")
    import traceback
    traceback.print_exc()

# Проверка хеширования пароля
print("\n4. Проверка хеширования пароля...")
try:
    test_password = "test123"
    hashed = User.hash_password(test_password)
    print(f"✓ Хеширование работает. Длина хеша: {len(hashed)}")
    
    # Проверка верификации
    test_user = User()
    test_user.hashed_password = hashed
    if test_user.verify_password(test_password):
        print("✓ Верификация пароля работает")
    else:
        print("✗ Верификация пароля не работает")
except Exception as e:
    print(f"✗ Ошибка хеширования: {e}")
    import traceback
    traceback.print_exc()

# Проверка ролей
print("\n5. Проверка ролей...")
try:
    roles = [r.value for r in UserRole]
    print(f"✓ Доступные роли: {', '.join(roles)}")
    
    # Проверка создания пользователя с ролью
    test_role = UserRole.TECHNICIAN
    print(f"✓ Роль '{test_role.value}' валидна")
except Exception as e:
    print(f"✗ Ошибка ролей: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("Отладка завершена")
print("=" * 50)

