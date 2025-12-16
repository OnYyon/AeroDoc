from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    title: str
    version: str
    author: str | None = None
    created_date: datetime | None = None
    modified_date: datetime | None = None
    file_type: str
    size: int
    checksum: str
    source: str


class DocumentChunk(BaseModel):
    id: str
    document_id: str
    content: str
    metadata: dict[str, Any]
    embedding: list[float] | None = None
    page_number: int | None = None
    section: str | None = None


class Document(BaseModel):
    id: str
    metadata: DocumentMetadata
    chunks: list[DocumentChunk]
    graph_nodes: list[dict[str, Any]] = []


class SearchQuery(BaseModel):
    query: str
    top_k: int = Field(default=10, ge=1, le=100)
    filters: dict[str, Any] | None = None


class SearchResult(BaseModel):
    chunk: DocumentChunk
    score: float
    document_metadata: DocumentMetadata
    source: str


class GraphNode(BaseModel):
    id: str
    label: str
    properties: dict[str, Any]


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str
    properties: dict[str, Any]


class GraphRAGResponse(BaseModel):
    answer: str
    sources: list[SearchResult]
    contradictions: list[str] = []
    outdated_info: list[str] = []


class UploadResponse(BaseModel):
    document_id: str
    status: str
    message: str
