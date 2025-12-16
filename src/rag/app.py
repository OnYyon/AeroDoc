from pathlib import Path
from typing import Optional

from src.rag.retriever import retrieve_context, retrieve_search_results
from src.rag.generator import generate_answer, generate_rag_response
from src.rag.ingest import ingest_from_directory
from src.rag.models import SearchQuery, GraphRAGResponse
from src.rag.logger import logger


def initialize_documents(force_update: bool = False) -> bool:
    """Инициализирует и загружает документы из директории documents.
    
    Args:
        force_update: Если True, переинициализирует все документы даже если они в БД
    """
    try:
        logger.info("Инициализация документов...")
        if force_update:
            logger.info("Режим принудительного обновления включен")
        
        documents = ingest_from_directory(force_update=force_update)
        
        if documents:
            logger.info(f"Успешно инициализировано {len(documents)} документов")
            return True
        else:
            logger.warning("Документы не были загружены")
            return False
    
    except Exception as e:
        logger.error(f"Ошибка при инициализации документов: {str(e)}")
        return False


def ask_question(question: str, n_context: int = 5) -> str:
    """Обрабатывает пользовательский запрос (простая версия)."""
    try:
        logger.info(f"Обработка вопроса: '{question}'")
        
        context_docs, metadatas, distances = retrieve_context(question, n_results=n_context)
        
        if not context_docs:
            logger.warning("Контекст не найден")
            return "Извините, я не смог найти релевантную информацию для вашего вопроса."
        
        context = "\n\n---\n\n".join(context_docs[:5])
        answer = generate_answer(question, context)
        
        response = f"**Вопрос:** {question}\n\n"
        response += f"**Ответ:** {answer}\n\n"
        response += "**Источники:**\n"
        
        for i, meta in enumerate(metadatas[:5], 1):
            src = Path(meta.get("source", "Unknown")).name
            score = 1 - (distances[i-1] / 2) if i-1 < len(distances) else 0
            response += f"{i}. {src} (релевантность: {score:.2f})\n"
        
        logger.info("Ответ успешно сформирован")
        return response
    
    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса: {str(e)}")
        return f"Произошла ошибка при обработке вашего запроса: {str(e)}"


def ask_question_advanced(question: str, top_k: int = 5) -> GraphRAGResponse:
    """Обрабатывает вопрос с использованием модели SearchQuery (расширенная версия)."""
    try:
        logger.info(f"Расширенная обработка вопроса: '{question}'")
        
        search_query = SearchQuery(
            query=question,
            top_k=min(top_k, 100),
            filters=None
        )
        
        search_results = retrieve_search_results(search_query)
        response = generate_rag_response(question, search_results)
        
        logger.info(f"Расширенный ответ сгенерирован")
        return response
    
    except Exception as e:
        logger.error(f"Ошибка при расширенной обработке вопроса: {str(e)}")
        return GraphRAGResponse(
            answer=f"Произошла ошибка при обработке запроса: {str(e)}",
            sources=[],
            contradictions=[],
            outdated_info=[]
        )


if __name__ == "__main__":
    logger.info("Запуск приложения RAG")
    
    # Инициализируем документы
    if not initialize_documents():
        logger.warning("Документы не были загружены. Продолжаем без инициализации.")
    
    # Простой пример
    question = "Что такое переменные в программировании?"
    logger.info(f"Тестовый вопрос: {question}")
    response = ask_question(question)
    print("\n" + "="*50)
    print(response)
    print("="*50)
