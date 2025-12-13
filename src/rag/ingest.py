from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
from typing import List, Dict
import markitdown

from src.rag.config import CHROMA_PATH, CHUNK_SIZE, CHUNK_OVERLAP, COLLECTION_NAME, EMBEDDING_MODEL


def load_pdf_content(pdf_path: str) -> str:
    """Извлекает текст из PDF."""
    text = ""
    with markitdown.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def split_document(content: str, source: str) -> List[Dict]:
    """Разбивает документ на чанки."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_text(content)
    return [
        {"content": chunk, "source": source}
        for chunk in chunks
    ]

def ingest_documents(doc_paths: List[str]):
    """Загружает, разбивает, векторизует и сохраняет документы."""
    model = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    all_chunks = []
    for path in doc_paths:
        content = load_pdf_content(path)
        chunks = split_document(content, path)
        all_chunks.extend(chunks)

    documents = [chunk["content"] for chunk in all_chunks]
    embeddings = model.encode(documents)

    metadatas = [{"source": chunk["source"]} for chunk in all_chunks]
    ids = [f"doc_{i}" for i in range(len(documents))]

    collection.add(
        documents=documents,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
        ids=ids
    )
    print(f"Ingested {len(all_chunks)} chunks into collection '{COLLECTION_NAME}'")
