"""
Примеры использования RAG приложения AeroDoc
Демонстрирует различные способы работы с системой
"""
from src.rag.app import ask_question, ask_question_advanced, initialize_documents
from src.rag.logger import logger


def example_simple_query():
    """Пример простого запроса."""
    logger.info("\n" + "="*60)
    logger.info("ПРИМЕР 1: Простой запрос")
    logger.info("="*60)
    
    question = "Что такое функции?"
    response = ask_question(question)
    print(response)


def example_advanced_query():
    """Пример расширенного запроса с моделями."""
    logger.info("\n" + "="*60)
    logger.info("ПРИМЕР 2: Расширенный запрос")
    logger.info("="*60)
    
    question = "Прочитай ap25-5ed-cons.pdf и расскажи пересказ"
    response = ask_question_advanced(question)
    
    print(f"\n**Вопрос:** {question}\n")
    print(f"**Ответ:** {response.answer}\n")
    print("**Источники:**")
    for i, source in enumerate(response.sources, 1):
        print(f"{i}. {source.source}")
        print(f"   Релевантность: {source.score:.2f}")
    
    if response.contradictions:
        print("\n**Противоречия:**")
        for contradiction in response.contradictions:
            print(f"  - {contradiction}")
    
    if response.outdated_info:
        print("\n**Устаревшая информация:**")
        for info in response.outdated_info:
            print(f"  - {info}")


def example_multiple_queries():
    """Пример нескольких последовательных запросов."""
    logger.info("\n" + "="*60)
    logger.info("ПРИМЕР 3: Несколько вопросов")
    logger.info("="*60)
    
    questions = [
        "Что такое переменная?",
        "Как работают условные операторы?",
        "Что такое список (array)?",
    ]
    
    for i, question in enumerate(questions, 1):
        logger.info(f"\nВопрос {i}: {question}")
        response = ask_question(question, n_context=3)
        print(f"\n{response}\n")


if __name__ == "__main__":
    logger.info("ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ RAG ПРИЛОЖЕНИЯ AERODOC")
    
    # Инициализируем документы
    logger.info("\nПрежде всего инициализируем документы...")
    if not initialize_documents():
        logger.warning("Документы не были загружены. Убедитесь, что файлы есть в папке documents/")
        exit(1)
    
    # Примеры
    try:
        example_simple_query()
        example_advanced_query()
        # example_multiple_queries()  # Раскомментируйте для запуска
    except Exception as e:
        logger.error(f"Ошибка при выполнении примеров: {e}", exc_info=True)
    
    logger.info("\n" + "="*60)
    logger.info("ПРИМЕРЫ ЗАВЕРШЕНЫ")
    logger.info("="*60)
