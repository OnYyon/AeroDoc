from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
from typing import List, Dict, Optional
from pathlib import Path
import markitdown
import hashlib
from datetime import datetime
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.rag.config import (
    CHROMA_PATH, CHUNK_SIZE, CHUNK_OVERLAP, COLLECTION_NAME, 
    EMBEDDING_MODEL, DOCUMENTS_DIR, SUPPORTED_FORMATS, 
    MAX_WORKERS, EMBEDDING_BATCH_SIZE, RETRY_ATTEMPTS
)
from src.rag.logger import logger
from src.rag.models import Document, DocumentMetadata, DocumentChunk
from src.rag.utils import retry_on_exception, batch_list, Timer, compute_file_hash


def get_file_checksum(file_path: str) -> str:
    """Вычисляет контрольную сумму файла."""
    return compute_file_hash(file_path, algorithm="md5")


def load_document_content(file_path: str) -> str:
    """Извлекает текст из различных форматов файлов."""
    path = Path(file_path)
    
    try:
        if path.suffix.lower() == ".pdf":
            logger.info(f"Загрузка PDF: {path.name}")
            # Используем markitdown для конвертации PDF в Markdown
            result = markitdown.MarkItDown().convert(str(path))
            # result это DocumentConverterResult с атрибутом text_content
            text = result.text_content if hasattr(result, 'text_content') else str(result)
            return text if text else ""
        elif path.suffix.lower() == ".txt":
            logger.info(f"Загрузка TXT: {path.name}")
            with open(str(path), "r", encoding="utf-8") as f:
                return f.read()
        elif path.suffix.lower() == ".md":
            logger.info(f"Загрузка Markdown: {path.name}")
            with open(str(path), "r", encoding="utf-8") as f:
                return f.read()
        else:
            logger.warning(f"Неподдерживаемый формат: {path.suffix}")
            return ""
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла {path}: {str(e)}")
        return ""


def split_document(content: str, source: str, document_id: str) -> List[DocumentChunk]:
    """Разбивает документ на чанки и создает объекты DocumentChunk."""
    if not content:
        logger.warning(f"Пустое содержимое для {source}")
        return []
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n"]  # Упрощенные сепараторы для скорости
    )
    chunks = splitter.split_text(content)
    
    document_chunks = []
    for i, chunk_content in enumerate(chunks):
        chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=document_id,
            content=chunk_content,
            metadata={"chunk_index": i, "source": source},
            page_number=None,
            section=None
        )
        document_chunks.append(chunk)
    
    logger.info(f"Документ разбит на {len(document_chunks)} чанков: {source}")
    return document_chunks


def create_document_metadata(file_path: str) -> DocumentMetadata:
    """Создает метаданные документа."""
    path = Path(file_path)
    
    return DocumentMetadata(
        title=path.stem,
        version="1.0",
        author="System",
        created_date=datetime.fromtimestamp(path.stat().st_ctime),
        modified_date=datetime.fromtimestamp(path.stat().st_mtime),
        file_type=path.suffix.lower(),
        size=path.stat().st_size,
        checksum=get_file_checksum(str(path)),
        source=str(path)
    )


def ingest_document(file_path: str) -> Optional[Document]:
    """Загружает, разбивает и подготавливает документ к сохранению."""
    path = Path(file_path)
    
    if not path.exists():
        logger.error(f"Файл не найден: {path}")
        return None
    
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        logger.warning(f"Неподдерживаемый формат файла: {path.suffix}")
        return None
    
    try:
        document_id = str(uuid.uuid4())
        content = load_document_content(str(path))
        
        if not content:
            logger.warning(f"Не удалось извлечь содержимое из: {path}")
            return None
        
        metadata = create_document_metadata(str(path))
        chunks = split_document(content, str(path), document_id)
        
        if not chunks:
            logger.warning(f"Нет чанков для документа: {path}")
            return None
        
        document = Document(
            id=document_id,
            metadata=metadata,
            chunks=chunks
        )
        
        logger.info(f"Документ успешно подготовлен: {path.name}")
        return document
    
    except Exception as e:
        logger.error(f"Ошибка при обработке документа {path}: {str(e)}")
        return None


def get_document_hash_from_db(source: str) -> Optional[str]:
    """Получает хеш документа из БД по источнику."""
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_collection(name=COLLECTION_NAME)

        # Ищем все чанки этого документа
        results = collection.get(
            where={"source": source},
            limit=1  # Нужен только один для получения хеша
        )

        if results and results["metadatas"] and len(results["metadatas"]) > 0:
            file_hash = results["metadatas"][0].get("file_hash")
            if file_hash:
                logger.debug(f"Найден хеш в БД для {Path(source).name}: {file_hash}")
                return file_hash
        logger.debug(f"Хеш не найден в БД для {source}")
        return None
    except Exception as e:
        logger.debug(f"Ошибка при получении хеша из БД: {str(e)}")
        return None


def should_process_file(file_path: str, force_update: bool = False) -> bool:
    """Проверяет, нужно ли обрабатывать файл по хешу."""
    try:
        file_name = Path(file_path).name
        current_hash = get_file_checksum(file_path)
        db_hash = get_document_hash_from_db(file_path)

        if db_hash is None:
            logger.info(f"Новый файл: {file_name}")
            return True

        if force_update:
            logger.info(f"Принудительное обновление: {file_name}")
            return True

        if db_hash == current_hash:
            logger.info(f"Пропуск (уже в БД): {file_name}")
            return False

        logger.info(f"Обновление (изменен): {file_name}")
        return True

    except Exception as e:
        logger.warning(f"Ошибка проверки {Path(file_path).name}: {str(e)}")
        return True


def ingest_documents_to_db(documents: List[Document]):
    """Сохраняет документы в Chroma DB с параллельной векторизацией."""
    if not documents:
        return

    try:
        with Timer("Сохранение документов в БД", log_level="info"):
            model = SentenceTransformer(EMBEDDING_MODEL)
            client = chromadb.PersistentClient(path=str(CHROMA_PATH))
            collection = client.get_or_create_collection(name=COLLECTION_NAME)

            total_chunks = 0

            for document in documents:
                chunk_contents = [chunk.content for chunk in document.chunks]
                
                if not chunk_contents:
                    logger.warning(f"Нет чанков для {Path(document.metadata.source).name}")
                    continue
                
                logger.info(
                    f"Векторизация {len(chunk_contents)} чанков "
                    f"для {Path(document.metadata.source).name}..."
                )
                
                # Обработка батчами для больших документов
                embeddings = []
                for batch in batch_list(chunk_contents, EMBEDDING_BATCH_SIZE):
                    batch_embeddings = model.encode(batch, show_progress_bar=False)
                    embeddings.extend(batch_embeddings)

                # Сохранение в батчах
                batch_size = 100
                for i in range(0, len(document.chunks), batch_size):
                    batch_chunks = document.chunks[i:i + batch_size]
                    batch_embeddings = embeddings[i:i + batch_size]
                    
                    for chunk, embedding in zip(batch_chunks, batch_embeddings):
                        metadata = {
                            "source": document.metadata.source,
                            "title": document.metadata.title,
                            "file_type": document.metadata.file_type,
                            "file_hash": document.metadata.checksum,
                            "chunk_index": chunk.metadata.get("chunk_index", 0)
                        }

                        collection.add(
                            documents=[chunk.content],
                            embeddings=[embedding.tolist()],
                            metadatas=[metadata],
                            ids=[chunk.id]
                        )
                        total_chunks += 1

            logger.info(f"Загружено {total_chunks} чанков в БД")

    except Exception as e:
        logger.error(f"Ошибка при сохранении: {str(e)}")


@retry_on_exception(max_attempts=RETRY_ATTEMPTS, delay=1.0, backoff=1.5)
def ingest_from_directory(directory: Optional[Path] = None, force_update: bool = False) -> List[Document]:
    """Загружает все поддерживаемые документы из директории (с проверкой по хешам)."""
    if directory is None:
        directory = DOCUMENTS_DIR

    directory = Path(directory)

    if not directory.exists():
        logger.error(f"Директория не найдена: {directory}")
        return []

    logger.info(f"Сканирование директории: {directory}")

    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_collection(name=COLLECTION_NAME)
        logger.info(f"Найдено {collection.count()} чанков в БД")
    except Exception:
        logger.info("БД пуста, начинаю первую загрузку")

    # Собираем файлы для обработки
    files_to_process = []
    skipped_count = 0

    for file_format in SUPPORTED_FORMATS:
        for file_path in directory.glob(f"*{file_format}"):
            file_path_str = str(file_path)
            if should_process_file(file_path_str, force_update):
                files_to_process.append(file_path_str)
            else:
                skipped_count += 1

    logger.info(f"К обработке: {len(files_to_process)}, пропущено: {skipped_count}")

    # Параллельная обработка файлов
    documents = []
    if files_to_process:
        logger.info(f"Запуск параллельной обработки ({MAX_WORKERS} worker'ов)...")
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(ingest_document, file_path): file_path 
                for file_path in files_to_process
            }
            
            for future in as_completed(futures):
                try:
                    document = future.result()
                    if document:
                        documents.append(document)
                except Exception as e:
                    file_path = futures[future]
                    logger.error(f"Ошибка при обработке {Path(file_path).name}: {str(e)}")

    if documents:
        logger.info(f"Загрузка {len(documents)} документов в БД...")
        ingest_documents_to_db(documents)
    else:
        if skipped_count > 0:
            logger.info("Все документы актуальны")
        else:
            logger.warning("Документы не найдены")

    return documents
