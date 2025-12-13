import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Dict

from src.rag.config import *

def retrieve_context(
    query: str,
    n_results: int = 5
) -> Tuple[List[str], List[Dict]]:
    """Ищет релевантные чанки по запросу."""
    model = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)

    query_embedding = model.encode([query])
    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    return documents, metadatas
