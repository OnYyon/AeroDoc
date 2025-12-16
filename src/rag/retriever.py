import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
from pathlib import Path

from src.rag.config import EMBEDDING_MODEL, CHROMA_PATH, COLLECTION_NAME, ENABLE_CACHE
from src.rag.logger import logger
from src.rag.models import SearchQuery, SearchResult, DocumentChunk, DocumentMetadata
from src.rag.utils import Timer, Cache, retry_on_exception

# Глобальный кеш для результатов поиска
_search_cache = Cache(ttl_seconds=3600) if ENABLE_CACHE else None


@retry_on_exception(max_attempts=3, delay=1.0, backoff=1.5)
def retrieve_context(
    query: str,
    n_results: int = 5,
    filters: Optional[Dict] = None,
    use_cache: bool = True
) -> tuple[List[str], List[Dict], List[float]]:
    """Ищет релевантные чанки по запросу с кешированием."""
    
    # Проверка кеша
    cache_key = f"{query}_{n_results}_{str(filters)}"
    if use_cache and _search_cache:
        cached_result = _search_cache.get(cache_key)
        if cached_result:
            logger.debug(f"Результат из кеша для запроса: '{query}'")
            return cached_result
    
    with Timer(f"Поиск по запросу: '{query}'", log_level="debug"):
        logger.info(f"Поиск по запросу: '{query}', количество результатов: {n_results}")
        
        model = SentenceTransformer(EMBEDDING_MODEL)
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        
        try:
            collection = client.get_collection(name=COLLECTION_NAME)
        except Exception as e:
            logger.error(f"Коллекция '{COLLECTION_NAME}' не найдена: {str(e)}")
            logger.info("Убедитесь, что документы загружены в БД")
            return [], [], []
        
        query_embedding = model.encode([query])
        results = collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=n_results,
            where=filters if filters else None,
            include=["documents", "metadatas", "distances"]
        )
        
        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []
        
        logger.info(f"Найдено {len(documents)} релевантных чанков")
        
        result = (documents, metadatas, distances)
        
        # Кешируем результат
        if _search_cache:
            _search_cache.set(cache_key, result)
        
        return result


def retrieve_search_results(
    query: SearchQuery,
    use_cache: bool = True
) -> List[SearchResult]:
    """Ищет документы и возвращает объекты SearchResult."""
    try:
        with Timer(f"Поиск SearchResults для: '{query.query}'", log_level="debug"):
            documents, metadatas, distances = retrieve_context(
                query.query,
                n_results=query.top_k,
                filters=query.filters,
                use_cache=use_cache
            )
            
            search_results = []
            for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
                score = max(0.0, 1.0 - distance)
                
                chunk = DocumentChunk(
                    id=metadata.get("id", f"chunk_{i}"),
                    document_id=metadata.get("document_id", "unknown"),
                    content=doc,
                    metadata=metadata,
                    page_number=metadata.get("page_number"),
                    section=metadata.get("section")
                )
                
                doc_metadata = DocumentMetadata(
                    title=metadata.get("title", "Unknown"),
                    version="1.0",
                    author=metadata.get("author"),
                    file_type=metadata.get("file_type", "unknown"),
                    size=metadata.get("size", 0),
                    checksum=metadata.get("checksum", ""),
                    source=metadata.get("source", "unknown")
                )
                
                result = SearchResult(
                    chunk=chunk,
                    score=score,
                    document_metadata=doc_metadata,
                    source=metadata.get("source", "unknown")
                )
                search_results.append(result)
            
            logger.info(f"Возвращено {len(search_results)} результатов поиска")
            return search_results
    
    except Exception as e:
        logger.error(f"Ошибка при поиске: {str(e)}")
        return []


def clear_cache():
    """Очищает кеш поиска."""
    if _search_cache:
        _search_cache.clear()
        logger.info("Кеш поиска очищен")
