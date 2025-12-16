import hashlib
import time
from pathlib import Path
from typing import Any, Dict
from functools import wraps

from src.rag.logger import logger


def compute_file_hash(file_path: str, algorithm: str = "md5") -> str:
    """Вычисляет хеш файла (по умолчанию MD5)."""
    try:
        hash_obj = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        logger.error(f"Ошибка при вычислении хеша {Path(file_path).name}: {str(e)}")
        return ""


def get_file_stats(file_path: str) -> Dict[str, Any]:
    """Получает статистику файла."""
    try:
        path = Path(file_path)
        if not path.exists():
            return {}
        
        stat = path.stat()
        return {
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "is_file": path.is_file(),
            "format": path.suffix.lower()
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики {Path(file_path).name}: {str(e)}")
        return {}


def retry_on_exception(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Декоратор для повторных попыток с экспоненциальной задержкой."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Попытка {attempt + 1}/{max_attempts} для {func.__name__} "
                            f"не удалась: {str(e)}. Повторение через {current_delay:.1f}с"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"Все {max_attempts} попытки для {func.__name__} не удались: {str(e)}"
                        )
            
            raise last_exception
        return wrapper
    return decorator


def safe_dict_get(d: Dict, key: str, default: Any = None) -> Any:
    """Безопасное получение значения из словаря с вложенными ключами."""
    try:
        keys = key.split(".")
        result = d
        for k in keys:
            result = result.get(k) if isinstance(result, dict) else None
            if result is None:
                return default
        return result
    except Exception:
        return default


def format_file_size(size: int) -> str:
    """Форматирует размер файла в читаемый вид."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def batch_list(items: list, batch_size: int) -> list[list]:
    """Разбивает список на батчи."""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def deduplicate_preserving_order(items: list) -> list:
    """Удаляет дубликаты, сохраняя порядок."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


class Timer:
    """Контекстный менеджер для измерения времени выполнения."""
    
    def __init__(self, name: str = "Operation", log_level: str = "info"):
        self.name = name
        self.log_level = log_level
        self.start_time = None
        self.elapsed = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, *args):
        self.elapsed = time.time() - self.start_time
        log_func = getattr(logger, self.log_level, logger.info)
        log_func(f"{self.name} выполнено за {self.elapsed:.2f}с")


class Cache:
    """Простой в памяти кеш с TTL."""
    
    def __init__(self, ttl_seconds: float = 3600):
        self.ttl = ttl_seconds
        self.cache: Dict[str, tuple[Any, float]] = {}
        
    def get(self, key: str, default: Any = None) -> Any:
        """Получает значение из кеша."""
        if key not in self.cache:
            return default
        
        value, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Сохраняет значение в кеш."""
        self.cache[key] = (value, time.time())
    
    def clear(self):
        """Очищает весь кеш."""
        self.cache.clear()
    
    def cleanup_expired(self):
        """Удаляет истёкшие записи."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"Очищено {len(expired_keys)} истёкших записей из кеша")
