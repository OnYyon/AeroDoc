import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
from pathlib import Path

from src.rag.config import EMBEDDING_MODEL, CHROMA_PATH, COLLECTION_NAME
from src.rag.logger import logger
from src.rag.models import SearchQuery, SearchResult, DocumentChunk, DocumentMetadata


def retrieve_context(
    query: str,
    n_results: int = 5,
    filters: Optional[Dict] = None
) -> tuple[List[str], List[Dict], List[float]]:
    """Ищет релевантные чанки по запросу."""
    try:
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
        return documents, metadatas, distances
    
    except Exception as e:
        logger.error(f"Ошибка при поиске контекста: {str(e)}")
        return [], [], []


def retrieve_search_results(
    query: SearchQuery
) -> List[SearchResult]:
    """Ищет документы и возвращает объекты SearchResult."""
    try:
        documents, metadatas, distances = retrieve_context(
            query.query,
            n_results=query.top_k,
            filters=query.filters
        )
        
        search_results = []
        for doc, metadata, distance in zip(documents, metadatas, distances):
            # Вычисляем score из distance (чем меньше distance, тем выше score)
            score = 1 - (distance / 2)  # Нормализуем в диапазон [0, 1]
            
            chunk = DocumentChunk(
                id=metadata.get("id", "unknown"),
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
