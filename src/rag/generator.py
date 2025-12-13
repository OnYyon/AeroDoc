from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

from src.rag.config import LLM_MODEL, TEMPERATURE

PROMPT_TEMPLATE = """\
You are a Python programming expert. Answer the question based on the provided context. \
Be specific about syntax and keywords. Include code examples if helpful.

Context:
{context}

Question:
{question}

Answer:"""

prompt = PromptTemplate(input_variables=["context", "question"], template=PROMPT_TEMPLATE)
llm = OllamaLLM(model=LLM_MODEL, temperature=TEMPERATURE)
chain = prompt | llm


def generate_answer(question: str, context: str) -> str:
    """Генерирует ответ на основе контекста."""
    answer = chain.invoke({"context": context, "question": question})
    return answer
