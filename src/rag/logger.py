import logging
from pathlib import Path

# Создать директорию для логов
logs_dir = Path("./logs")
logs_dir.mkdir(exist_ok=True)

# Настроить логирование
logger = logging.getLogger("rag")
logger.setLevel(logging.DEBUG)

# Файловый обработчик
file_handler = logging.FileHandler(logs_dir / "rag.log")
file_handler.setLevel(logging.DEBUG)

# Консольный обработчик
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Формат логов
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Добавить обработчики
logger.addHandler(file_handler)
logger.addHandler(console_handler)
