"""Vector store protocol and ChromaDB implementation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MemoryEntry(BaseModel):
    """A single entry retrieved from memory."""

    id: str
    text: str
    metadata: dict[str, Any] = {}
    distance: float = 0.0  # similarity distance (lower = more similar)


class VectorStore(ABC):
    """Abstract interface for vector storage backends."""

    @abstractmethod
    async def add(
        self,
        collection: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> str:
        """Store a document with its embedding. Returns the document ID."""

    @abstractmethod
    async def query(
        self,
        collection: str,
        embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[MemoryEntry]:
        """Query for similar documents."""

    @abstractmethod
    async def delete(self, collection: str, ids: list[str]) -> None:
        """Delete documents by ID."""

    @abstractmethod
    async def count(self, collection: str) -> int:
        """Count documents in a collection."""


class ChromaDBStore(VectorStore):
    """ChromaDB implementation of VectorStore."""

    def __init__(self, persist_dir: Path) -> None:
        import chromadb

        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collections: dict[str, Any] = {}
        logger.info("ChromaDB initialized at %s", persist_dir)

    def _get_collection(self, name: str) -> Any:
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name, metadata={"hnsw:space": "cosine"}
            )
        return self._collections[name]

    async def add(
        self,
        collection: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> str:
        from uuid import uuid4

        col = self._get_collection(collection)
        doc_id = doc_id or uuid4().hex
        col.add(
            ids=[doc_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata or {}],
        )
        return doc_id

    async def query(
        self,
        collection: str,
        embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[MemoryEntry]:
        col = self._get_collection(collection)

        kwargs: dict[str, Any] = {
            "query_embeddings": [embedding],
            "n_results": min(n_results, col.count() or 1),
        }
        if where:
            kwargs["where"] = where

        if col.count() == 0:
            return []

        results = col.query(**kwargs)

        entries = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                entries.append(
                    MemoryEntry(
                        id=doc_id,
                        text=results["documents"][0][i] if results["documents"] else "",
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                        distance=results["distances"][0][i] if results["distances"] else 0.0,
                    )
                )
        return entries

    async def delete(self, collection: str, ids: list[str]) -> None:
        col = self._get_collection(collection)
        col.delete(ids=ids)

    async def count(self, collection: str) -> int:
        col = self._get_collection(collection)
        return col.count()
