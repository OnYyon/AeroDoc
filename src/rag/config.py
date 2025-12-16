from pathlib import Path
import os

# Paths
BASE_DIR = Path(__file__).parent
DOCUMENTS_DIR = BASE_DIR / "documents"
CHROMA_PATH = BASE_DIR / "chroma_db"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DOCUMENTS_DIR.mkdir(exist_ok=True, parents=True)
CHROMA_PATH.mkdir(exist_ok=True, parents=True)
LOGS_DIR.mkdir(exist_ok=True, parents=True)

# Document processing - оптимизировано для скорости
CHUNK_SIZE = 400  # Меньше - быстрее обработка
CHUNK_OVERLAP = 50  # Меньше пересечение
SUPPORTED_FORMATS = [".pdf", ".txt", ".md"]
MAX_WORKERS = min(8, os.cpu_count() or 1)  # Больше параллельных потоков

# Embedding and LLM - легкие модели для скорости
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Быстрая и легкая модель
LLM_MODEL = "llama3:latest"
TEMPERATURE = 0.1
COLLECTION_NAME = "aerodoc_collection"
TOP_K_DEFAULT = 3  # Меньше результатов по умолчанию

# Performance - оптимизировано
EMBEDDING_BATCH_SIZE = 64  # Больше батчей для GPU
CHROMA_TIMEOUT = 15  # Быстрее timeout
RETRY_ATTEMPTS = 2  # Меньше попыток
RETRY_DELAY = 0.5  # Быстрее повторы

# Features
AUTO_BACKGROUND_INGEST = True
ENABLE_CACHE = True
CACHE_TTL_SECONDS = 3600
