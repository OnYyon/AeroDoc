from langchain_core.prompts import PromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path
from collections import Counter
from sentence_transformers import SentenceTransformer

# # 1. Настраиваем сплиттер
# text_splitter = RecursiveCharacterTextSplitter(
#     chunk_size=600,
#     chunk_overlap=120,
#     separators=["\n\n", "\n", ". ", " ", ""]
# )
#
# # 2. Загружаем содержимое документа (пример для PDF)
# def load_pdf_content(pdf_path: str) -> str:
#     """Пример функции для загрузки текста из PDF."""
#     try:
#         from markitdown import MarkItDown
#         md = MarkItDown()
#         result = md.convert(pdf_path)
#         return result.text_content
#     except Exception as e:
#         print(f"Ошибка загрузки PDF: {e}")
#         return ""
#
# # 3. Создаём структуру документа с реальным содержимым
# source_path = "./documents/think_python_guide.pdf"
# content = load_pdf_content(source_path)
#
# processed_document = {
#     'source': source_path,
#     'content': content  # Теперь здесь реальный текст
# }
#
# # 4. Список документов (теперь содержит данные)
# documents = [processed_document]
#
# # 5. Функция обработки документа
# def process_document(doc, text_splitter):
#     """Обрабатывает документ в чанки."""
#     doc_chunks = text_splitter.split_text(doc["content"])
#     return [
#         {"content": chunk, "source": doc["source"]}
#         for chunk in doc_chunks
#     ]
#
# # 6. Обработка и сбор чанков
# all_chunks = []
# for doc in documents:
#     doc_chunks = process_document(doc, text_splitter)
#     all_chunks.extend(doc_chunks)
#
# # 7. Анализ результатов
# if all_chunks:  # Проверяем, что чанки созданы
#     source_counts = Counter(chunk["source"] for chunk in all_chunks)
#     chunk_lengths = [len(chunk["content"]) for chunk in all_chunks]
#
#     print(f"Total chunks created: {len(all_chunks)}")
#     print(f"Chunk length: {min(chunk_lengths)}-{max(chunk_lengths)} characters")
#     print(f"Source document: {Path(documents[0]['source']).name}")
# else:
#     print("No chunks were created. Check if the document was loaded correctly.")
#
#
# # Load Q&A-optimized embedding model (downloads automatically on first use)
# model = SentenceTransformer('multi-qa-mpnet-base-dot-v1')
#
# # Extract documents and create embeddings
# documents = [chunk["content"] for chunk in all_chunks]
# embeddings = model.encode(documents)
#
# print(f"Embedding generation results:")
# print(f"  - Embeddings shape: {embeddings.shape}")
# print(f"  - Vector dimensions: {embeddings.shape[1]}")
#
# from sentence_transformers import util
#
# query = "How do you define functions in Python?"
# document_chunks = [
#     "Variables store data values that can be used later in your program.",
#     "A function is a block of code that performs a specific task when called.",
#     "Loops allow you to repeat code multiple times efficiently.",
#     "Functions can accept parameters and return values to the calling code."
# ]
#
# # Encode query and documents
# query_embedding = model.encode(query)
# doc_embeddings = model.encode(document_chunks)
#
# similarities = util.cos_sim(query_embedding, doc_embeddings)[0]
#
# # Create ranked results
# ranked_results = sorted(
#     zip(document_chunks, similarities),
#     key=lambda x: x[1],
#     reverse=True
# )
#
# print(f"Query: '{query}'")
# print("Document chunks ranked by relevance:")
# for i, (chunk, score) in enumerate(ranked_results, 1):
#     print(f"{i}. ({score:.3f}): '{chunk}'")
#
#
# import chromadb
#
# # Create persistent client for data storage
# client = chromadb.PersistentClient(path="./chroma_db")
#
# # Create collection for business documents (or get existing)
# collection = client.get_or_create_collection(
#     name="python_guide",
#     metadata={"description": "Python programming guide"}
# )
#
# print(f"Created collection: {collection.name}")
# print(f"Collection ID: {collection.id}")
#
# metadatas = [{"document": Path(chunk["source"]).name} for chunk in all_chunks]
#
# collection.add(
#     documents=documents,
#     embeddings=embeddings.tolist(), # Convert numpy array to list
#     metadatas=metadatas, # Metadata for each document
#     ids=[f"doc_{i}" for i in range(len(documents))], # Unique identifiers for each document
# )
#
# print(f"Collection count: {collection.count()}")\
import chromadb
client = chromadb.PersistentClient(path="./chroma_db")
model = SentenceTransformer('multi-qa-mpnet-base-dot-v1')
collection = client.get_or_create_collection(
    name="python_guide",
    metadata={"description": "Python programming guide"}
)
def format_query_results(question, query_embedding, documents, metadatas):
    """Format and print the search results with similarity scores"""
    from sentence_transformers import util

    print(f"Question: {question}\n")

    for i, doc in enumerate(documents):
        # Calculate accurate similarity using sentence-transformers util
        doc_embedding = model.encode([doc])
        similarity = util.cos_sim(query_embedding, doc_embedding)[0][0].item()
        source = metadatas[i].get("document", "Unknown")

        print(f"Result {i+1} (similarity: {similarity:.3f}):")
        print(f"Document: {source}")
        print(f"Content: {doc[:300]}...")
        print()


def query_knowledge_base(question, n_results=2):
    """Query the knowledge base with natural language"""
    # Encode the query using our SentenceTransformer model
    query_embedding = model.encode([question])

    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    # Extract results and format them
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    format_query_results(question, query_embedding, documents, metadatas)

query_knowledge_base("How do if-else statements work in Python?")

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
llm = OllamaLLM(model="llama3.1:8b", temperature=0.1)
prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are a Python programming expert. Based on the provided documentation, answer the question clearly and accurately.

Documentation:
{context}

Question: {question}

Answer (be specific about syntax, keywords, and provide examples when helpful):"""
)
chain = prompt_template | llm

def retrieve_context(question, n_results=5):
    """Retrieve relevant context using embeddings"""
    query_embedding = model.encode([question])
    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    documents = results["documents"][0]
    context = "\n\n---SECTION---\n\n".join(documents)
    return context, documents


def get_llm_answer(question, context):
    """Generate answer using retrieved context"""
    answer = chain.invoke(
        {
            "context": context[:2000],
            "question": question,
        }
    )
    return answer


def format_response(question, answer, source_chunks):
    """Format the final response with sources"""
    response = f"**Question:** {question}\n\n"
    response += f"**Answer:** {answer}\n\n"
    response += "**Sources:**\n"

    for i, chunk in enumerate(source_chunks[:3], 1):
        preview = chunk[:100].replace("\n", " ") + "..."
        response += f"{i}. {preview}\n"

    return response


def enhanced_query_with_llm(question, n_results=1):
    """Query function combining retrieval with LLM generation"""
    context, documents = retrieve_context(question, n_results)
    answer = get_llm_answer(question, context)
    return format_response(question, answer, documents)


enhanced_response = enhanced_query_with_llm("How do if-else statements work in Python?")
print(enhanced_response)
