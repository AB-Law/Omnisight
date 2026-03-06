import pytest
from unittest.mock import MagicMock, patch
from intelligence_api.application.processor import IntelligenceProcessor

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def processor(mock_db):
    with patch("intelligence_api.application.processor.SemanticCache"), \
         patch("intelligence_api.application.processor.AIClient"):
        proc = IntelligenceProcessor(mock_db)
        return proc

def test_hash_pii_logic(processor):
    raw_event = {
        "entity_label": "JohnDoe",
        "content": "Secret info",
        "source_type": "Twitter",
        "is_user": True
    }
    
    with patch("intelligence_api.application.processor.hash_pii", return_value="hashed_val") as mock_hash:
        processor.ai.get_embedding.return_value = [0.1] * 1536
        processor.cache.check_cache.return_value = {"sentiment": 0.5}
        
        # Mock DB query to return None (new entity)
        processor.db.query().filter().first.return_value = None
        
        import asyncio
        asyncio.run(processor.process_event(raw_event))
        
        mock_hash.assert_called_once_with("JohnDoe")

def test_cache_hit_prevents_ai_call(processor):
    raw_event = {"content": "test", "entity_label": "test", "source_type": "test"}
    
    processor.ai.get_embedding.return_value = [0.1] * 1536
    processor.cache.check_cache.return_value = {"sentiment": 0.8, "summary": "cached", "category": "test"}
    
    import asyncio
    asyncio.run(processor.process_event(raw_event))
    
    processor.ai.analyze_content.assert_not_called()
