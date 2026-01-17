import json
from openai import OpenAI
from typing import Optional

from app.core.config import Settings
from app.models.schemas import ChunkMetadata, QueryResponse, Citation


class LLMService:
    """
    Service for generating answers using OpenAI with citations.
    
    Uses structured output to ensure consistent JSON responses
    with answer, confidence, and source citations.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)
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
        
        # Call OpenAI
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=self.max_tokens,
            temperature=0.1,  # Low temperature for factual responses
            response_format={"type": "json_object"}
        )
        
        # Parse response
        content = response.choices[0].message.content
        result = json.loads(content)
        
        # Build citations from the response
        citations = self._build_citations(result.get("citations", []), relevant_chunks)
        
        return QueryResponse(
            answer=result.get("answer", "Unable to generate an answer."),
            confidence=min(max(result.get("confidence", 0.5), 0), 1),
            citations=citations,
            processing_time_ms=0  # Will be set by the route
        )
    
    def _build_context(
        self,
        chunks: list[tuple[ChunkMetadata, float]]
    ) -> str:
        """Build context string from chunks with source references."""
        context_parts = []
        
        for i, (chunk, score) in enumerate(chunks, 1):
            context_parts.append(
                f"[Source {i}] (Document: {chunk.document_name}, Page: {chunk.page_number})\n"
                f"{chunk.text}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM."""
        return """You are a helpful assistant that answers questions based on provided document excerpts.

Your task is to:
1. Answer the question using ONLY the information from the provided sources
2. Cite your sources by referencing the source numbers [Source N]
3. If the sources don't contain enough information, say so clearly
4. Be concise but thorough

You MUST respond with a valid JSON object in this exact format:
{
    "answer": "Your detailed answer here with inline citations like [Source 1]",
    "confidence": 0.85,
    "citations": [
        {
            "source_number": 1,
            "relevance": "Brief explanation of why this source is relevant"
        }
    ]
}

The confidence score should be:
- 0.9-1.0: Answer is directly stated in sources
- 0.7-0.9: Answer can be inferred from sources
- 0.5-0.7: Partial information available
- Below 0.5: Limited relevant information

Always include at least one citation if you provide an answer."""
    
    def _get_user_prompt(self, question: str, context: str) -> str:
        """Get the user prompt with question and context."""
        return f"""Question: {question}

Sources:
{context}

Please answer the question based on the sources above. Remember to respond with valid JSON."""
    
    def _build_citations(
        self,
        citation_refs: list[dict],
        chunks: list[tuple[ChunkMetadata, float]]
    ) -> list[Citation]:
        """Build Citation objects from LLM response and chunk data."""
        citations = []
        
        for ref in citation_refs:
            source_num = ref.get("source_number", 1)
            idx = source_num - 1
            
            if 0 <= idx < len(chunks):
                chunk, score = chunks[idx]
                
                # Create excerpt (first 200 chars)
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
