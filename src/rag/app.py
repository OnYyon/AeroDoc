from pathlib import Path
from typing import Optional
import atexit

from src.rag.retriever import retrieve_context, retrieve_search_results, clear_cache
from src.rag.generator import generate_answer, generate_rag_response
from src.rag.ingest import ingest_from_directory
from src.rag.models import SearchQuery, GraphRAGResponse
from src.rag.logger import logger
from src.rag.worker import init_workers, shutdown_workers, submit_background_task
from src.rag.config import AUTO_BACKGROUND_INGEST


class RAGService:
    """Основной сервис RAG."""
    
    def __init__(self, auto_ingest: bool = True):
        self.initialized = False
        self.documents_loaded = False
        
        if auto_ingest:
            init_workers()
            atexit.register(shutdown_workers)
            logger.info("RAGService инициализирован с фоновым обновлением")
        else:
            logger.info("RAGService инициализирован без фонового обновления")
    
    def initialize_documents(self, force_update: bool = False) -> bool:
        """Инициализирует и загружает документы."""
        try:
            logger.info("Инициализация документов...")
            documents = ingest_from_directory(force_update=force_update)
            
            if documents:
                logger.info(f"Успешно инициализировано {len(documents)} документов")
                self.documents_loaded = True
                self.initialized = True
                return True
            else:
                logger.warning("Документы не были загружены")
                self.initialized = True
                return False
        
        except Exception as e:
            logger.error(f"Ошибка при инициализации документов: {str(e)}")
            return False
    
    def background_update_documents(self):
        """Запускает фоновое обновление документов."""
        if AUTO_BACKGROUND_INGEST:
            submit_background_task(ingest_from_directory, force_update=False)
    
    def ask_question(self, question: str, n_context: int = 5) -> str:
        """Обрабатывает вопрос (простая версия)."""
        try:
            logger.info(f"Обработка вопроса: '{question}'")
            
            context_docs, metadatas, distances = retrieve_context(
                question,
                n_results=n_context,
                use_cache=True
            )
            
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
                score = max(0.0, 1.0 - distances[i-1]) if i-1 < len(distances) else 0
                response += f"{i}. {src} (релевантность: {score:.2f})\n"
            
            logger.info("Ответ успешно сформирован")
            return response
        
        except Exception as e:
            logger.error(f"Ошибка при обработке вопроса: {str(e)}")
            return f"Произошла ошибка при обработке вашего запроса: {str(e)}"
    
    def ask_question_advanced(self, question: str, top_k: int = 5) -> GraphRAGResponse:
        """Обрабатывает вопрос с расширенной информацией."""
        try:
            logger.info(f"Расширенная обработка вопроса: '{question}'")
            
            search_query = SearchQuery(
                query=question,
                top_k=min(top_k, 100),
                filters=None
            )
            
            search_results = retrieve_search_results(search_query, use_cache=True)
            response = generate_rag_response(question, search_results)
            
            logger.info("Расширенный ответ сгенерирован")
            return response
        
        except Exception as e:
            logger.error(f"Ошибка при расширенной обработке: {str(e)}")
            return GraphRAGResponse(
                answer=f"Произошла ошибка: {str(e)}",
                sources=[],
                contradictions=[],
                outdated_info=[]
            )
    
    def refresh_cache(self):
        """Очищает кеш поиска."""
        clear_cache()
        logger.info("Кеш очищен")
    
    def batch_ask_questions(self, questions: list[str]) -> list[str]:
        """Обрабатывает список вопросов."""
        results = []
        for question in questions:
            result = self.ask_question(question)
            results.append(result)
        return results


# Глобальный экземпляр сервиса
_service: Optional[RAGService] = None


def get_service() -> RAGService:
    """Получает глобальный экземпляр сервиса (ленивая инициализация)."""
    global _service
    if _service is None:
        _service = RAGService(auto_ingest=AUTO_BACKGROUND_INGEST)
    return _service


def initialize_documents(force_update: bool = False) -> bool:
    """Инициализирует документы."""
    return get_service().initialize_documents(force_update=force_update)


def ask_question(question: str, n_context: int = 5) -> str:
    """Публичный API для задания вопроса."""
    return get_service().ask_question(question, n_context)


def ask_question_advanced(question: str, top_k: int = 5) -> GraphRAGResponse:
    """Публичный API для расширенного запроса."""
    return get_service().ask_question_advanced(question, top_k)


def refresh_cache():
    """Публичный API для очистки кеша."""
    return get_service().refresh_cache()


if __name__ == "__main__":
    logger.info("=== Запуск RAG приложения ===")
    
    service = get_service()
    
    if not service.initialize_documents():
        logger.warning("Не удалось загрузить документы")
    
    print("\nДобро пожаловать в RAG систему!")
    print("Введите вопрос (или 'выход' для завершения)\n")
    
    while True:
        try:
            question = input("Вопрос: ").strip()
            
            if question.lower() in ['выход', 'exit', 'quit']:
                logger.info("Завершение работы")
                print("До свидания!")
                break
            
            if not question:
                continue
            
            response = service.ask_question(question)
            print("\n" + response + "\n")
            print("-" * 80 + "\n")
        
        except KeyboardInterrupt:
            logger.info("Прерывание пользователем")
            print("\n\nПрограмма прервана")
            break
        except Exception as e:
            logger.error(f"Ошибка: {str(e)}")
            print(f"Ошибка: {str(e)}\n")
