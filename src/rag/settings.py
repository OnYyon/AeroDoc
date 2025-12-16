from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Vector DB
    vector_db_path: str = "./data/vector.db"
    embedding_db_model: str = "multi-qa-mpnet-base-dot-v1"

    # Graph DB
    graph_db_path: str = "./data/graph.db"

    # API
    host: str = "localhost"
    port: int = 8000

    # LLM
    llm_model: str = "llama3:latest"
    ollama_base_url: str = "http://localhost:11434"

    # Chunks
    chunk_size: int = 10000
    chunk_overlap: int = 200
    max_workers: int = 4

    # Storage
    documents_path: str = "./data/documents"

    class Config:
        env_file: str = "./.env"


settings = Settings()
