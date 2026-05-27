from __future__ import annotations

import json
import uuid
from typing import Optional

import numpy as np
from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.core.config import Settings
from app.models.schemas import Citation, QueryResponse
from app.services.embedding_service import EmbeddingService


class SemanticCacheService:
    """
    Redis-backed semantic cache for near-duplicate query responses.
    """

    def __init__(self, settings: Settings, embedding_service: EmbeddingService):
        self.settings = settings
        self.embedding_service = embedding_service
        self.redis = Redis.from_url(settings.redis_url, decode_responses=False)
        self.index_name = settings.redis_index_name
        self.key_prefix = settings.redis_key_prefix
        self.similarity_threshold = settings.cache_similarity_threshold
        self.ttl_seconds = settings.cache_ttl_seconds

    async def ensure_index(self) -> None:
        """
        Ensure RediSearch vector index exists for semantic lookups.
        """
        try:
            await self.redis.execute_command("FT.INFO", self.index_name)
            return
        except ResponseError:
            pass

        dimension = self.embedding_service.dimension
        await self.redis.execute_command(
            "FT.CREATE",
            self.index_name,
            "ON",
            "HASH",
            "PREFIX",
            "1",
            self.key_prefix,
            "SCHEMA",
            "query",
            "TEXT",
            "response",
            "TEXT",
            "embedding",
            "VECTOR",
            "HNSW",
            "6",
            "TYPE",
            "FLOAT32",
            "DIM",
            str(dimension),
            "DISTANCE_METRIC",
            "COSINE",
        )

    async def get_cached_response(self, query: str) -> Optional[QueryResponse]:
        """
        Return cached QueryResponse when semantic similarity threshold is met.
        """
        await self.ensure_index()
        query_embedding = self.embedding_service.embed_query(query).astype(np.float32)
        embedding_bytes = query_embedding.tobytes()

        result = await self.redis.execute_command(
            "FT.SEARCH",
            self.index_name,
            "*=>[KNN 1 @embedding $embedding AS score]",
            "PARAMS",
            "2",
            "embedding",
            embedding_bytes,
            "SORTBY",
            "score",
            "ASC",
            "RETURN",
            "2",
            "response",
            "score",
            "DIALECT",
            "2",
        )

        if not result or result[0] == 0:
            return None

        fields = result[2]
        payload = {fields[i].decode("utf-8"): fields[i + 1] for i in range(0, len(fields), 2)}
        score = float(payload["score"])
        similarity = 1.0 - score

        if similarity < self.similarity_threshold:
            return None

        response_json = payload["response"]
        if isinstance(response_json, bytes):
            response_json = response_json.decode("utf-8")
        response_data = json.loads(response_json)
        response_data.setdefault("processing_time_ms", 0)
        return QueryResponse(
            answer=response_data["answer"],
            confidence=response_data["confidence"],
            citations=[Citation(**c) for c in response_data.get("citations", [])],
            processing_time_ms=response_data["processing_time_ms"],
        )

    async def cache_response(
        self,
        query: str,
        query_embedding: np.ndarray,
        response: QueryResponse,
    ) -> None:
        """
        Cache query embedding and response payload with TTL.
        """
        await self.ensure_index()
        key = f"{self.key_prefix}{uuid.uuid4()}"
        payload = {
            "answer": response.answer,
            "confidence": response.confidence,
            "citations": [citation.model_dump() for citation in response.citations],
            "processing_time_ms": response.processing_time_ms,
        }
        await self.redis.hset(
            key,
            mapping={
                "query": query,
                "response": json.dumps(payload),
                "embedding": query_embedding.astype(np.float32).tobytes(),
            },
        )
        await self.redis.expire(key, self.ttl_seconds)
