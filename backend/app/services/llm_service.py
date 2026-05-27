import instructor
from openai import APIConnectionError, APIError, APIStatusError, OpenAI, RateLimitError
from pydantic import ValidationError
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from app.core.config import Settings
from app.models.schemas import ChunkMetadata, QueryResponse, Citation, ExtractedInsight


class LLMService:
    """
    Service for generating answers using OpenAI with strict schema enforcement.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = instructor.from_openai(OpenAI(api_key=settings.openai_api_key))
        self.model = settings.openai_model
        self.max_tokens = settings.max_tokens
    
    def generate_answer(
        self,
        question: str,
        relevant_chunks: list[tuple[ChunkMetadata, float]]
    ) -> QueryResponse:
        """
        Generate an answer with citations using OpenAI.
        
        Args:
            question: User's question
            relevant_chunks: List of (chunk, relevance_score) tuples
            
        Returns:
            QueryResponse with answer, confidence, and citations
        """
        # Build context from chunks
        context = self._build_context(relevant_chunks)
        
        # Create prompt
        system_prompt = self._get_system_prompt()
        user_prompt = self._get_user_prompt(question, context)
        
        structured_result = self._generate_structured_answer(system_prompt, user_prompt)
        citations = self._build_citations(structured_result.citations, relevant_chunks)
        
        return QueryResponse(
            answer=structured_result.answer,
            confidence=min(max(structured_result.confidence_score, 0), 1),
            citations=citations,
            processing_time_ms=0  # Will be set by the route
        )

    def _generate_structured_answer(self, system_prompt: str, user_prompt: str) -> ExtractedInsight:
        validation_feedback = ""
        retryer = Retrying(
            stop=stop_after_attempt(4),
            wait=wait_random_exponential(multiplier=1, max=30),
            retry=retry_if_exception_type(
                (RateLimitError, APIConnectionError, APIStatusError, APIError, ValidationError)
            ),
            reraise=True,
        )

        for attempt in retryer:
            with attempt:
                prompt = system_prompt
                if validation_feedback:
                    prompt = (
                        f"{system_prompt}\n\n"
                        "The last attempt failed schema validation. "
                        f"Validation trace: {validation_feedback}\n"
                        "Return output strictly matching the schema."
                    )

                try:
                    return self.client.chat.completions.create(
                        model=self.model,
                        response_model=ExtractedInsight,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        max_tokens=self.max_tokens,
                        temperature=0.1,
                    )
                except ValidationError as exc:
                    validation_feedback = str(exc)
                    raise

        raise RuntimeError("Unable to generate a structured response.")
    
    def _build_context(
        self,
        chunks: list[tuple[ChunkMetadata, float]]
    ) -> str:
        """Build context string from chunks with source references."""
        context_parts = []
        
        for i, (chunk, _score) in enumerate(chunks, 1):
            context_parts.append(
                f"[Source {i}] (Chunk ID: {chunk.chunk_id}, Document: {chunk.document_name}, Page: {chunk.page_number})\n"
                f"{chunk.text}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM."""
        return """You are a helpful assistant that answers questions based on provided document excerpts.

Your task is to:
1. Answer the question using ONLY the information from the provided sources
2. Cite your sources by listing the exact chunk IDs used
3. If the sources don't contain enough information, say so clearly
4. Be concise but thorough

The confidence score should be:
- 0.9-1.0: Answer is directly stated in sources
- 0.7-0.9: Answer can be inferred from sources
- 0.5-0.7: Partial information available
- Below 0.5: Limited relevant information

Always include at least one chunk ID in citations if you provide an answer."""
    
    def _get_user_prompt(self, question: str, context: str) -> str:
        """Get the user prompt with question and context."""
        return f"""Question: {question}

Sources:
{context}

Please answer the question based on the sources above. Return output in the schema format."""
    
    def _build_citations(
        self,
        citation_refs: list[str],
        chunks: list[tuple[ChunkMetadata, float]]
    ) -> list[Citation]:
        """Build Citation objects from LLM response and chunk data."""
        citations = []
        chunk_map = {chunk.chunk_id: (chunk, score) for chunk, score in chunks}

        for chunk_id in citation_refs:
            matched = chunk_map.get(chunk_id)
            if matched is None:
                continue

            chunk, score = matched
            excerpt = chunk.text[:200]
            if len(chunk.text) > 200:
                excerpt += "..."

            citations.append(Citation(
                document_name=chunk.document_name,
                page_number=chunk.page_number,
                text_excerpt=excerpt,
                relevance_score=score
            ))
        
        # If no citations from LLM, use top chunks
        if not citations and chunks:
            for chunk, score in chunks[:3]:
                excerpt = chunk.text[:200]
                if len(chunk.text) > 200:
                    excerpt += "..."
                
                citations.append(Citation(
                    document_name=chunk.document_name,
                    page_number=chunk.page_number,
                    text_excerpt=excerpt,
                    relevance_score=score
                ))
        
        return citations
