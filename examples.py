#!/usr/bin/env python
"""
Примеры использования RAG сервиса.
Демонстрирует простой и расширенный API.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.rag.app import (
    ask_question,
    ask_question_advanced,
    initialize_documents, get_service
)
from src.rag.logger import logger
from src.rag.config import COLLECTION_NAME, CHROMA_PATH
import chromadb


def check_db_initialized() -> bool:
    """Проверяет, инициализирована ли БД."""
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_collection(name=COLLECTION_NAME)
        chunk_count = collection.count()
        logger.info(f"БД содержит {chunk_count} чанков")
        return chunk_count > 0
    except Exception:
        logger.info("БД пуста или не инициализирована")
        return False


def auto_initialize_if_needed() -> bool:
    """Автоматически инициализирует БД если она пуста."""
    if not check_db_initialized():
        logger.info("БД пуста, запуск инициализации через initialize_documents...")
        try:
            success = initialize_documents(force_update=False)
            if success:
                logger.info("БД успешно инициализирована")
                return True
            else:
                logger.error("Ошибка при инициализации БД")
                return False
        except Exception as e:
            logger.error(f"Ошибка при инициализации: {str(e)}")
            return False
    
    return True


def example_simple_query():
    """Простой пример запроса."""
    logger.info("\n" + "=" * 70)
    logger.info("ПРИМЕР 1: Простой запрос")
    logger.info("=" * 70)
    
    question = "Как работает система?"
    print(f"\nВопрос: {question}\n")
    
    response = ask_question(question, n_context=5)
    print(response)


def example_advanced_query():
    """Расширенный пример запроса с источниками."""
    logger.info("\n" + "=" * 70)
    logger.info("ПРИМЕР 2: Расширенный запрос с источниками")
    logger.info("=" * 70)
    
    question = "Какие требования предъявляются к летной годности самолетов транспортной категории?"
    print(f"\nВопрос: {question}\n")
    
    response = ask_question_advanced(question, top_k=5)
    
    print(f"Ответ: {response.answer}\n")
    print("Источники:")
    for i, source in enumerate(response.sources, 1):
        source_file = Path(source.source).name
        print(f"  {i}. {source_file} (релевантность: {source.score:.2f})")
        print(f"     {source.chunk.content[:100]}...\n")

def main():
    logger.info("=" * 70)
    logger.info("Запуск примеров RAG системы")
    logger.info("=" * 70)
    
    # Проверяем и инициализируем БД если нужно
    if not auto_initialize_if_needed():
        logger.error("Не удалось инициализировать БД")
        print("\nОшибка: БД не инициализирована. Убедитесь, что:")
        print("  1. Documents находятся в src/rag/documents/")
        print("  2. Запустите: python ingest_runner.py")
        return 1
    
    # Загружаем документы в сервис
    logger.info("\nЗагрузка документов в сервис...")
    if not initialize_documents():
        logger.warning("Документы не загружены (возможно, уже в БД)")
    
    # Примеры
    try:
        print("\n")
        example_advanced_query()
        
        logger.info("\n" + "=" * 70)
        logger.info("Все примеры выполнены успешно")
        logger.info("=" * 70)
        
        print("\nДля интерактивного режима запустите: python -m src.rag.app")
        return 0
    
    except Exception as e:
        logger.error(f"Ошибка при выполнении примеров: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
