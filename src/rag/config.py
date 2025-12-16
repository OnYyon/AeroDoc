from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DOCUMENTS_DIR = BASE_DIR / "documents"
CHROMA_PATH = BASE_DIR / "chroma_db"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DOCUMENTS_DIR.mkdir(exist_ok=True)
CHROMA_PATH.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Document processing
CHUNK_SIZE = 600
CHUNK_OVERLAP = 120
SUPPORTED_FORMATS = [".pdf", ".txt", ".md"]

# Embedding and LLM
EMBEDDING_MODEL = "multi-qa-mpnet-base-dot-v1"
LLM_MODEL = "llama3.1:8b"
TEMPERATURE = 0.1
COLLECTION_NAME = "aerodoc_collection"
