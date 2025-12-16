from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from typing import List

from src.rag.config import LLM_MODEL, TEMPERATURE
from src.rag.logger import logger
from src.rag.models import SearchResult, GraphRAGResponse

PROMPT_TEMPLATE = """\
Ты — эксперт по работе с официальной документацией. Твоя задача — отвечать строго на основе предоставленного контекста, не придумывая и не домысливая ничего сверх того, что явно указано в документе.

Отвечай чётко, логично и без галлюцинаций. Если информация в контексте отсутствует, прямо скажи: «В предоставленном контексте недостаточно информации для ответа».

Обязательно указывай прямую цитату из документа, на которую ты ссылаешься, и поясняй, как именно она относится к вопросу.

Контекст:
{context}

Вопрос:
{question}

Ответ:
"""

def generate_answer(question: str, context: str) -> str:
    """Генерирует ответ на основе контекста."""
    try:
        logger.info(f"Генерация ответа на вопрос: '{question}'")
        
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=PROMPT_TEMPLATE
        )
        
        llm = OllamaLLM(model=LLM_MODEL, temperature=TEMPERATURE)
        chain = prompt | llm
        
        answer = chain.invoke({"context": context, "question": question})
        logger.info("Ответ успешно сгенерирован")
        return answer
    
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {str(e)}")
        return "Извините, не удалось сгенерировать ответ. Пожалуйста, попробуйте позже."

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
        
        # Формируем контекст из найденных результатов
        context_parts = []
        for i, result in enumerate(search_results[:5], 1):
            source_name = result.source.split("/")[-1]
            context_parts.append(
                f"[Источник {i}: {source_name}]\n{result.chunk.content}"
            )
        
        context = "\n\n---\n\n".join(context_parts)
        answer = generate_answer(question, context)
        
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
