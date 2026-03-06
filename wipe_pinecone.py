import pinecone
from intelligence_api.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WipePinecone")

def main():
    logger.info(f"Connecting to Pinecone index: {settings.PINECONE_INDEX}")
    try:
        pc = pinecone.Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX)
        
        logger.info("Deleting all vectors from the index...")
        # Note: delete_all=True is the standard way to wipe an entire index/namespace
        index.delete(delete_all=True)
        
        logger.info("Successfully wiped Pinecone index.")
    except Exception as e:
        logger.error(f"Failed to wipe Pinecone: {e}")

if __name__ == "__main__":
    main()
