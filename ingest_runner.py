"""
Скрипт для загрузки документов в ChromaDB
Поддерживает форматы: PDF, TXT, MD

Использование:
    python ingest_runner.py           # Загружает только новые/измененные документы
    python ingest_runner.py --force   # Переинициализирует все документы
"""
import sys
from pathlib import Path
from src.rag.ingest import ingest_from_directory, SUPPORTED_FORMATS
from src.rag.logger import logger

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Запуск скрипта загрузки документов в ChromaDB")
    logger.info("=" * 60)
    
    # Проверяем аргументы командной строки
    force_update = "--force" in sys.argv or "-f" in sys.argv
    if force_update:
        logger.info("✓ Режим принудительного обновления включен")
        logger.info("  Все документы будут переинициализированы")
    
    # Путь к папке documents
    documents_dir = Path("./src/rag/documents")
    
    if not documents_dir.exists():
        logger.error(f"Директория не найдена: {documents_dir}")
        logger.info("Создание пустой директории...")
        documents_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Директория создана: {documents_dir}")
        logger.info(f"Поддерживаемые форматы: {', '.join(SUPPORTED_FORMATS)}")
        logger.info("Пожалуйста, поместите документы в эту директорию")
    else:
        # Поиск всех поддерживаемых файлов
        all_files = []
        for file_format in SUPPORTED_FORMATS:
            files = list(documents_dir.glob(f"*{file_format}"))
            all_files.extend(files)
        
        if not all_files:
            logger.warning(f"В директории {documents_dir} нет поддерживаемых файлов")
            logger.info(f"Поддерживаемые форматы: {', '.join(SUPPORTED_FORMATS)}")
            logger.info("Пожалуйста, добавьте документы в директорию")
        else:
            logger.info(f"Найдено файлов: {len(all_files)}")
            for file in sorted(all_files):
                logger.info(f"  ✓ {file.name} ({file.suffix})")
            
            # Загрузить документы
            try:
                logger.info("\nНачало обработки документов...")
                documents = ingest_from_directory(documents_dir, force_update=force_update)
                logger.info("=" * 60)
                logger.info(f"✓ Успешно обработано документов: {len(documents)}")
                logger.info("✓ Документы загружены в ChromaDB")
                logger.info("=" * 60)
            except Exception as e:
                logger.error(f"✗ Ошибка при загрузке документов: {e}", exc_info=True)
                logger.info("=" * 60)
