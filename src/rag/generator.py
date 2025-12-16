from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from typing import List

from src.rag.config import LLM_MODEL, TEMPERATURE, RETRY_ATTEMPTS
from src.rag.logger import logger
from src.rag.models import SearchResult, GraphRAGResponse
from src.rag.utils import retry_on_exception, Timer

PROMPT_TEMPLATE = """\
Ты — квалифицированный специалист в области авиастроения и авиационной техники. Твоя задача — анализировать технические документы и давать точные, информативные ответы на вопросы, связанные с конструкцией, системами, технического обслуживания и эксплуатации летательных аппаратов.

КРИТИЧЕСКИЕ ТРЕБОВАНИЯ:
1. Используй ТОЛЬКО информацию из предоставленного контекста
2. Цитируй точные технические характеристики, параметры и размеры
3. Указывай стандарты и регламенты (ГОСТ, SNECMA, АД и т.д.)
4. Если данных недостаточно, скажи: "В документации недостаточно информации для полного ответа"
5. Выделяй критические параметры для безопасности (пределы температуры, нагрузки, ресурс)

ФОРМАТ ОТВЕТА:
- Начни с краткого резюме
- Приведи технические детали с ссылками на документ
- Указывай единицы измерения (кН, об/мин, часы, км)
- Выделяй ограничения и условия применения

Технический контекст:
{context}

Техническая задача:
{question}

Ответ специалиста:
"""


@retry_on_exception(max_attempts=RETRY_ATTEMPTS, delay=2.0, backoff=1.5)
def generate_answer(question: str, context: str) -> str:
    """Генерирует ответ на основе контекста с повторными попытками."""
    try:
        with Timer(f"Генерация ответа на: '{question}'", log_level="debug"):
            logger.info(f"Генерация ответа на вопрос: '{question}'")
            
            prompt = PromptTemplate(
                input_variables=["context", "question"],
                template=PROMPT_TEMPLATE
            )
            
            llm = OllamaLLM(model=LLM_MODEL, temperature=TEMPERATURE)
            chain = prompt | llm
            
            answer = chain.invoke({"context": context, "question": question})
            logger.info("Ответ успешно сгенерирован")
            return answer if answer else "Не удалось сгенерировать ответ"
    
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {str(e)}")
        raise


def generate_rag_response(
    question: str,
    search_results: List[SearchResult]
) -> GraphRAGResponse:
    """Генерирует полный RAG ответ с источниками."""
    try:
        if not search_results:
            logger.warning(f"Нет результатов поиска для вопроса: '{question}'")
            return GraphRAGResponse(
                answer="Не найдены релевантные источники для ответа на ваш вопрос.",
                sources=[],
                contradictions=[],
                outdated_info=[]
            )
        
        with Timer("Генерация RAG ответа", log_level="debug"):
            # Формируем контекст из найденных результатов
            context_parts = []
            for i, result in enumerate(search_results[:5], 1):
                source_name = result.source.split("/")[-1]
                context_parts.append(
                    f"[Источник {i}: {source_name} (релевантность: {result.score:.2f})]"
                    f"\n{result.chunk.content}"
                )
            
            context = "\n\n---\n\n".join(context_parts)
            
            try:
                answer = generate_answer(question, context)
            except Exception as e:
                logger.warning(f"Ошибка при генерации: {str(e)}, используем стандартный ответ")
                answer = "Не удалось сгенерировать ответ из-за ошибки в системе. Попробуйте позже."
            
            response = GraphRAGResponse(
                answer=answer,
                sources=search_results[:5],
                contradictions=[],
                outdated_info=[]
            )
            
            logger.info(f"RAG ответ сгенерирован с {len(search_results)} источниками")
            return response

    except Exception as e:
        logger.error(f"Ошибка при генерации RAG ответа: {str(e)}")
        return GraphRAGResponse(
            answer="Произошла ошибка при обработке запроса.",
            sources=[],
            contradictions=[],
            outdated_info=[]
        )
