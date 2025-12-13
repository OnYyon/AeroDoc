from src.rag.retriever import retrieve_context
from generator import generate_answer
from pathlib import Path


def ask_question(question: str, n_context: int = 1) -> str:
    """Обрабатывает пользовательский запрос."""
    context_docs, metadatas = retrieve_context(question, n_results=n_context)
    context = "\n\n---\n\n".join(context_docs[:3])
    answer = generate_answer(question, context)

    response = f"**Вопрос:** {question}\n\n"
    response += f"**Ответ:** {answer}\n\n"
    response += "**Источники:**\n"
    for i, meta in enumerate(metadatas[:3], 1):
        src = Path(meta.get("source", "Unknown")).name
        response += f"{i}. {src}\n"

    return response


if __name__ == "__main__":
    question = "Как работают if‑else конструкции в Python?"
    response = ask_question(question)
    print(response)
