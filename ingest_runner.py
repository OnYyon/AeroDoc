#!/usr/bin/env python
"""
Standalone скрипт для загрузки и обновления документов в ChromaDB.
Поддерживает флаги: --force для переинициализации всех документов.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.rag.ingest import ingest_from_directory
from src.rag.logger import logger
from src.rag.utils import Timer


def main():
    parser = argparse.ArgumentParser(
        description="Загрузить документы в ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
    python ingest_runner.py              # Загрузить новые/изменённые документы
    python ingest_runner.py --force      # Перезагрузить все документы
        """
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Переинициализировать все документы"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("Запуск загрузки документов в ChromaDB")
    logger.info("=" * 70)
    
    if args.force:
        logger.info("Режим: Принудительное обновление ВСЕх документов")
    else:
        logger.info("Режим: Обновление только новых/изменённых документов")
    
    try:
        with Timer("Полная обработка документов", log_level="info"):
            documents = ingest_from_directory(force_update=args.force)
        
        logger.info("=" * 70)
        if documents:
            total_chunks = sum(len(doc.chunks) for doc in documents)
            logger.info(f"✓ Успешно: {len(documents)} документов, {total_chunks} чанков")
            logger.info("✓ Документы загружены в ChromaDB")
        else:
            logger.info("✓ Все документы актуальны, обновлений не требуется")
        logger.info("=" * 70)
        return 0
    
    except Exception as e:
        logger.error(f"✗ Ошибка: {str(e)}", exc_info=True)
        logger.info("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
