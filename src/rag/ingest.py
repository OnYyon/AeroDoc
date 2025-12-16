from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
from typing import List, Dict, Optional
from pathlib import Path
import markitdown
import hashlib
from datetime import datetime
import uuid

from src.rag.config import CHROMA_PATH, CHUNK_SIZE, CHUNK_OVERLAP, COLLECTION_NAME, EMBEDDING_MODEL, DOCUMENTS_DIR, SUPPORTED_FORMATS
from src.rag.logger import logger
from src.rag.models import Document, DocumentMetadata, DocumentChunk


def get_file_checksum(file_path: str) -> str:
    """Вычисляет контрольную сумму файла."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


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
        separators=["\n\n", "\n", ". ", " ", ""]
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
    """Получает хеш документа из БД по источнику (получает все и выбирает первый)."""
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


def delete_document_from_db(source: str):
    """Удаляет все чанки документа из БД по источнику."""
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_collection(name=COLLECTION_NAME)
        
        # Ищем все чанки этого документа
        results = collection.get(
            where={"source": source}
        )
        
        if results and results["ids"]:
            collection.delete(ids=results["ids"])
            logger.info(f"Удалено {len(results['ids'])} чанков для источника: {source}")
    except Exception as e:
        logger.debug(f"Не удалось удалить документ: {str(e)}")


def ingest_documents_to_db(documents: List[Document], force_update: bool = False):
    """Сохраняет документы в Chroma DB (проверка хешей уже сделана в ingest_from_directory)."""
    if not documents:
        logger.warning("Список документов пуст")
        return
    
    try:
        model = SentenceTransformer(EMBEDDING_MODEL)
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_or_create_collection(name=COLLECTION_NAME)
        
        total_chunks = 0
        
        for document in documents:
            # Загружаем чанки и добавляем в БД
            chunk_contents = [chunk.content for chunk in document.chunks]
            logger.info(f"Векторизация {len(chunk_contents)} чанков для {Path(document.metadata.source).name}...")
            embeddings = model.encode(chunk_contents)
            
            for chunk, embedding in zip(document.chunks, embeddings):
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
        
        logger.info(f"✅ Успешно загружено {total_chunks} чанков в коллекцию '{COLLECTION_NAME}'")
    
    except Exception as e:
        logger.error(f"Ошибка при сохранении документов в БД: {str(e)}")
        raise


def ingest_from_directory(directory: Optional[Path] = None, force_update: bool = False) -> List[Document]:
    """Загружает все поддерживаемые документы из директории (с проверкой по хешам)."""
    if directory is None:
        directory = DOCUMENTS_DIR
    
    directory = Path(directory)
    
    if not directory.exists():
        logger.error(f"Директория не найдена: {directory}")
        return []
    
    logger.info(f"Сканирование директории: {directory}")
    
    # Проверяем наличие коллекции
    collection_exists = False
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_collection(name=COLLECTION_NAME)
        logger.info(f"Коллекция найдена: {collection.count()} чанков в БД")
        collection_exists = True
    except Exception as e:
        logger.info(f"Коллекция не найдена, будет создана при загрузке документов")
        collection_exists = False
    
    documents_to_process = []
    skipped_files = 0
    
    # ПЕРВЫЙ ПРОХОД: фильтруем файлы по хешам БЕЗ загрузки
    for file_format in SUPPORTED_FORMATS:
        for file_path in directory.glob(f"*{file_format}"):
            try:
                file_name = file_path.name
                file_path_str = str(file_path)
                
                # Вычисляем хеш текущего файла
                current_hash = get_file_checksum(file_path_str)
                
                # Получаем хеш из БД если коллекция существует
                if collection_exists:
                    db_hash = get_document_hash_from_db(file_path_str)
                else:
                    db_hash = None
                
                # Проверяем логику
                if db_hash is not None:
                    # Файл есть в БД
                    if db_hash == current_hash and not force_update:
                        # Файл не изменился - пропускаем
                        logger.info(f"⏭️  Пропуск (уже в БД): {file_name} [хеш совпадает]")
                        skipped_files += 1
                        continue
                    else:
                        # Файл изменился - обновляем
                        logger.info(f"🔄 Обновление (хеш изменился): {file_name}")
                        delete_document_from_db(file_path_str)
                else:
                    # Файла нет в БД - это новый файл
                    logger.info(f"➕ Новый файл: {file_name}")
                
                # Добавляем в список на обработку
                documents_to_process.append(file_path_str)
                
            except Exception as e:
                logger.error(f"Ошибка при проверке хеша {file_path.name}: {str(e)}")
                continue
    
    logger.info(f"Результаты сканирования: пропущено {skipped_files} файлов, к обработке {len(documents_to_process)}")
    
    # ВТОРОЙ ПРОХОД: загружаем и обрабатываем только нужные файлы
    documents = []
    for file_path_str in documents_to_process:
        logger.info(f"Обработка файла: {Path(file_path_str).name}")
        document = ingest_document(file_path_str)
        if document:
            documents.append(document)
    
    if documents:
        logger.info(f"Загружено {len(documents)} документов, начинаю инжестию в БД...")
        ingest_documents_to_db(documents, force_update=False)
    else:
        if skipped_files > 0:
            logger.info(f"✅ Все {skipped_files} документов уже в БД с актуальными хешами")
        else:
            logger.warning(f"Документы не найдены в {directory}")
    
    return documents
