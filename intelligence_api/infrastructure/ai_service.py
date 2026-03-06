import hashlib
from typing import Optional, Dict, Any, List
import pinecone
from intelligence_api.core.config import settings

class SemanticCache:
    def __init__(self):
        # Initializing Pinecone client (using the new 3.x+ syntax if available, 
        # but sticking to basic initialization for compatibility)
        self.pc = pinecone.Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index = self.pc.Index(settings.PINECONE_INDEX)

    def _generate_id(self, text: str) -> str:
        return hashlib.md5(text.strip().lower().encode()).hexdigest()

    def check_cache(self, embedding: List[float], threshold: float = 0.95) -> Optional[Dict[str, Any]]:
        """Queries Pinecone for a semantic match."""
        try:
            results = self.index.query(
                vector=embedding, 
                top_k=1, 
                include_metadata=True
            )
            if results.matches and results.matches[0].score >= threshold:
                metadata = dict(results.matches[0].metadata)
                # De-serialize mentioned_entities if present
                if "mentioned_entities" in metadata and isinstance(metadata["mentioned_entities"], str):
                    import json
                    try:
                        metadata["mentioned_entities"] = json.loads(metadata["mentioned_entities"])
                    except:
                        pass
                return metadata
        except Exception as e:
            print(f"Cache query error: {e}")
        return None

    def store(self, text: str, embedding: List[float], metadata: Dict[str, Any]):
        """Stores analysis result in Pinecone."""
        doc_id = self._generate_id(text)
        # Serialize mentioned_entities for Pinecone (doesn't support nested lists of dicts)
        clean_metadata = dict(metadata)
        if "mentioned_entities" in clean_metadata and not isinstance(clean_metadata["mentioned_entities"], str):
            import json
            clean_metadata["mentioned_entities"] = json.dumps(clean_metadata["mentioned_entities"])
            
        try:
            self.index.upsert(vectors=[(doc_id, embedding, clean_metadata)])
        except Exception as e:
            print(f"Cache storage error: {e}")

    def delete_by_filter(self, filter_dict: Dict[str, Any]):
        """Delete vectors match a filter (e.g. {'entity_label': 'Apple'})"""
        try:
            self.index.delete(filter=filter_dict)
        except Exception as e:
            print(f"Pinecone deletion error: {e}")

class AIClient:
    def __init__(self):
        from openai import AzureOpenAI
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2023-05-15",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )

    def get_embedding(self, text: str) -> List[float]:
        # Log input for debugging
        print(f"DEBUG: Generating embedding for model: '{settings.AZURE_EMBEDDING_DEPLOYMENT}'")
        print(f"DEBUG: Text length: {len(text)}")
        
        if not text.strip():
            print("WARNING: Empty text passed to get_embedding")
            return [0.0] * 1536
            
        try:
            response = self.client.embeddings.create(
                input=[text], # Reverting to list[str]
                model=settings.AZURE_EMBEDDING_DEPLOYMENT
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Azure OpenAI Embedding Error: {e}")
            print(f"DEBUG: Endpoint used: {settings.AZURE_OPENAI_ENDPOINT}")
            raise

    def analyze_content(self, text: str) -> Dict[str, Any]:
        """Performs sentiment analysis, categorization, entity enrichment, and NER extraction."""
        prompt = f"""
        Analyze the following text for an OSINT platform focused on Market Intelligence.
        
        Provide the following details in your analysis:
        1. **Sentiment Score**: A float between -1.0 (extremely bearish/negative) and 1.0 (extremely bullish/positive).
           - **CRITICAL**: Evaluate sentiment based on the potential impact on **Stock Price**, **Investor Confidence**, and **Entity Reputation**.
           - Do not assume a business event (like ending an investment or a strategic shift) is inherently positive or negative. 
           - **Evaluate the context**: Determine if the event is a sign of weakness/risk (Bearish) or a sign of strategic strength/capital allocation efficiency (Bullish).
        2. **Summary**: A concise 1-sentence summary of the event.
        3. **Category**: A relevance categorization (e.g., 'Financial Move', 'Product Launch', 'Legal/Regulatory', 'Market Rumor', 'Partnership Update').
        4. **Sector**: The industry sector of the primary company/entity mentioned (e.g., 'Technology', 'Finance', 'Energy', etc.).
        5. **Entity Description**: A brief 1-sentence description of the primary company mentioned.
        6. **Mentioned Entities**: Extract ALL named entities from the text. For each entity provide:
           - name: The entity's canonical name (e.g. "Elon Musk", "Tesla"). 
           - type: One of PERSON, COMPANY, ORG, LOCATION, PRODUCT, or TOPIC.
           - relevance_score: An integer from 1-10 (10 being most critical/central to the text).
           
           **STRICT NER RULES**:
           - **COMPANY**: Extract companies, organizations, and institutional bodies. **HIGHLIGHT ALL RELEVANT COMPANIES** even if the text is primarily about a Person.
           - **PERSON**: Extract ONLY actual names of individuals.
           - **LOCATION**: Extract Countries, Cities, or Regions (e.g., "India", "Paris"). 
           - **BLACKLIST**: DO NOT extract generic titles (CEO, Founder, etc.).
           
           Limit to the 10 most relevant. Return an empty list if none found.
        
        Text: {text}
        
        Return JSON ONLY in this format:
        {{"sentiment": 0.5, "summary": "...", "category": "...", "sector": "...", "entity_description": "...", "mentioned_entities": [{{"name": "Tesla", "type": "COMPANY", "relevance_score": 10}}, {{"name": "Elon Musk", "type": "PERSON", "relevance_score": 9}}]}}
        """
        
        response = self.client.chat.completions.create(
            model=settings.AZURE_CHAT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        import json
        return json.loads(response.choices[0].message.content)
